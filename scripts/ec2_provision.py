#!/usr/bin/env python3
"""
AWS EC2 Deployment Script for AI Health Companion
Uses boto3 — runs inside Docker container
"""
import boto3, json, time, sys, os, base64, textwrap

# ── Credentials ───────────────────────────────────────────────────────────────
# Set these via environment variables or aws configure — never hard-code keys
AWS_ACCESS_KEY    = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY    = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
REGION            = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
KEY_NAME          = "ai-health-key"
SG_NAME           = "ai-health-sg"
INSTANCE_NAME     = "ai-health-companion"
INSTANCE_TYPE     = "t2.micro"
UBUNTU_OWNER      = "099720109477"

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION
)
ec2 = session.client("ec2")
ec2r = session.resource("ec2")

def log(msg):  print(f"  ➜  {msg}")
def ok(msg):   print(f"  ✅ {msg}")
def warn(msg): print(f"  ⚠️  {msg}")

print("\n" + "="*60)
print("  AI Health Companion — EC2 Deployment via boto3")
print("  Region:", REGION, "| Type:", INSTANCE_TYPE, "(Free Tier)")
print("="*60 + "\n")

# ── Step 1: Verify account ────────────────────────────────────────────────────
sts = session.client("sts")
identity = sts.get_caller_identity()
ok(f"AWS Account: {identity['Account']}")

# ── Step 2: Get your public IP ────────────────────────────────────────────────
import urllib.request
my_ip = urllib.request.urlopen("https://api.ipify.org").read().decode().strip()
ok(f"Your public IP: {my_ip}")

# ── Step 3: Create SSH Key Pair ───────────────────────────────────────────────
log("Setting up SSH key pair...")
KEY_FILE = "/tmp/ai-health-key.pem"
try:
    existing = ec2.describe_key_pairs(KeyNames=[KEY_NAME])
    ok(f"Key pair '{KEY_NAME}' already exists in AWS")
    if not os.path.exists(KEY_FILE):
        warn(f"Key file not found at {KEY_FILE} — will create new key pair")
        ec2.delete_key_pair(KeyName=KEY_NAME)
        raise Exception("recreate")
except ec2.exceptions.ClientError:
    kp = ec2.create_key_pair(KeyName=KEY_NAME)
    with open(KEY_FILE, "w") as f:
        f.write(kp["KeyMaterial"])
    os.chmod(KEY_FILE, 0o400)
    ok(f"Key pair created → {KEY_FILE}")

# ── Step 4: Create Security Group ────────────────────────────────────────────
log("Setting up security group...")
vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
vpc_id = vpcs["Vpcs"][0]["VpcId"]

sgs = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [SG_NAME]}])
if sgs["SecurityGroups"]:
    sg_id = sgs["SecurityGroups"][0]["GroupId"]
    ok(f"Security group already exists: {sg_id}")
else:
    sg = ec2.create_security_group(
        GroupName=SG_NAME,
        Description="AI Health Companion - port 80 public, port 22 your IP only",
        VpcId=vpc_id
    )
    sg_id = sg["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[
        {"IpProtocol": "tcp", "FromPort": 22,  "ToPort": 22,
         "IpRanges": [{"CidrIp": f"{my_ip}/32", "Description": "SSH admin only"}]},
        {"IpProtocol": "tcp", "FromPort": 80,  "ToPort": 80,
         "IpRanges": [{"CidrIp": "0.0.0.0/0",  "Description": "HTTP public"}]},
    ])
    ok(f"Security group created: {sg_id}")

# ── Step 5: Find Ubuntu 22.04 AMI ────────────────────────────────────────────
log("Finding latest Ubuntu 22.04 LTS AMI...")
images = ec2.describe_images(
    Owners=[UBUNTU_OWNER],
    Filters=[
        {"Name": "name",   "Values": ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]},
        {"Name": "state",  "Values": ["available"]},
    ]
)
ami = sorted(images["Images"], key=lambda x: x["CreationDate"])[-1]
ami_id = ami["ImageId"]
ok(f"AMI: {ami_id} ({ami['Name'][:50]})")

# ── Step 6: Check for existing instance ──────────────────────────────────────
log("Checking for existing instance...")
existing = ec2.describe_instances(Filters=[
    {"Name": "tag:Name",            "Values": [INSTANCE_NAME]},
    {"Name": "instance-state-name", "Values": ["running", "stopped", "pending"]},
])
instance_id = None
ec2_ip = None
if existing["Reservations"]:
    inst = existing["Reservations"][0]["Instances"][0]
    instance_id = inst["InstanceId"]
    ec2_ip = inst.get("PublicIpAddress")
    ok(f"Instance already exists: {instance_id}  IP: {ec2_ip}")

# ── Step 7: Launch instance ───────────────────────────────────────────────────
if not instance_id:
    log("Launching t2.micro EC2 instance (Free Tier)...")
    user_data = textwrap.dedent("""
        #!/bin/bash
        exec >> /var/log/ai-health-init.log 2>&1
        echo "=== AI Health Companion Boot Init ==="
        apt-get update -y
        apt-get install -y curl git ca-certificates
        curl -fsSL https://get.docker.com | bash
        usermod -aG docker ubuntu
        systemctl enable docker
        systemctl start docker
        echo "=== Docker installed ==="
    """).strip()

    result = ec2.run_instances(
        ImageId=ami_id,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SecurityGroupIds=[sg_id],
        MinCount=1, MaxCount=1,
        BlockDeviceMappings=[{
            "DeviceName": "/dev/sda1",
            "Ebs": {"VolumeSize": 20, "VolumeType": "gp2", "DeleteOnTermination": True}
        }],
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": INSTANCE_NAME}]
        }],
        UserData=user_data,
    )
    instance_id = result["Instances"][0]["InstanceId"]
    ok(f"Instance launched: {instance_id}")

# ── Step 8: Wait for running ──────────────────────────────────────────────────
log("Waiting for instance to be running...")
waiter = ec2.get_waiter("instance_running")
waiter.wait(InstanceIds=[instance_id])
ok("Instance is running")

# ── Step 9: Get public IP ─────────────────────────────────────────────────────
for attempt in range(10):
    inst_info = ec2.describe_instances(InstanceIds=[instance_id])
    ec2_ip = inst_info["Reservations"][0]["Instances"][0].get("PublicIpAddress")
    if ec2_ip:
        break
    time.sleep(5)
ok(f"Public IP: {ec2_ip}")

# ── Step 10: Wait for SSH ─────────────────────────────────────────────────────
import socket
log("Waiting for SSH port 22 to open (up to 3 min)...")
for attempt in range(36):
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((ec2_ip, 22))
        s.close()
        ok("SSH is ready")
        break
    except:
        print(f"    Attempt {attempt+1}/36 — waiting 5s...", flush=True)
        time.sleep(5)

# ── Output results ────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  INSTANCE READY")
print("="*60)
print(f"  instance_id : {instance_id}")
print(f"  public_ip   : {ec2_ip}")
print(f"  key_file    : {KEY_FILE}")
print(f"  ssh_cmd     : ssh -o StrictHostKeyChecking=no -i {KEY_FILE} ubuntu@{ec2_ip}")
print("="*60 + "\n")

# Write results to file for next step
with open("/tmp/ec2-result.json", "w") as f:
    json.dump({"instance_id": instance_id, "ec2_ip": ec2_ip, "key_file": KEY_FILE}, f)

print("DEPLOYMENT_READY")



