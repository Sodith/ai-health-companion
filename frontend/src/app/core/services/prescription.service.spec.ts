import { TestBed } from "@angular/core/testing";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";
import { PrescriptionService } from "./prescription.service";
import { environment } from "../../../environments/environment";
const BASE = `${environment.apiUrl}/prescriptions`;
describe("PrescriptionService", () => {
  let service: PrescriptionService;
  let httpMock: HttpTestingController;
  const mockList = { success: true, status_code: 200, message: "OK", error: null, data: [{ id: 1, original_file_name: "rx.pdf", file_type: "pdf", file_size: 102400, symptoms: "headache", upload_status: "processed", created_at: new Date().toISOString() }] };
  const mockUpload = { success: true, status_code: 201, message: "Uploaded.", error: null, data: { upload_id: 42, filename: "uuid.pdf", status: "uploaded" } };
  const mockDetail = { success: true, status_code: 200, message: "OK", error: null, data: { id: 1, user_id: "uid", original_file_name: "rx.pdf", stored_file_name: "u.pdf", file_path: "up/rx.pdf", file_type: "pdf", file_size: 102400, symptoms: null, upload_status: "processed", created_at: new Date().toISOString(), updated_at: new Date().toISOString() } };
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [PrescriptionService, provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(PrescriptionService);
    httpMock = TestBed.inject(HttpTestingController);
  });
  afterEach(() => httpMock.verify());
  it("should be created", () => { expect(service).toBeTruthy(); });
  it("should GET all prescriptions", () => {
    let r: any;
    service.getAll().subscribe(x => (r = x));
    const req = httpMock.expectOne(BASE);
    expect(req.request.method).toBe("GET");
    req.flush(mockList);
    expect(r.data.length).toBe(1);
    expect(r.data[0].original_file_name).toBe("rx.pdf");
  });
  it("should GET a single prescription by id", () => {
    let r: any;
    service.getById(1).subscribe(x => (r = x));
    const req = httpMock.expectOne(`${BASE}/1`);
    expect(req.request.method).toBe("GET");
    req.flush(mockDetail);
    expect(r.data.id).toBe(1);
  });
  it("should POST FormData with file and symptoms", () => {
    const file = new File(["content"], "rx.pdf", { type: "application/pdf" });
    let r: any;
    service.upload(file, "headache").subscribe(x => (r = x));
    const req = httpMock.expectOne(`${BASE}/upload`);
    expect(req.request.method).toBe("POST");
    expect(req.request.body instanceof FormData).toBe(true);
    expect(req.request.body.get("symptoms")).toBe("headache");
    req.flush(mockUpload);
    expect(r.data.upload_id).toBe(42);
  });
  it("should POST FormData without symptoms when null", () => {
    const file = new File(["content"], "rx.png", { type: "image/png" });
    service.upload(file, null).subscribe();
    const req = httpMock.expectOne(`${BASE}/upload`);
    expect(req.request.body.get("symptoms")).toBeNull();
    req.flush(mockUpload);
  });
  it("should not append empty/whitespace symptoms", () => {
    const file = new File(["content"], "rx.jpg", { type: "image/jpeg" });
    service.upload(file, "   ").subscribe();
    const req = httpMock.expectOne(`${BASE}/upload`);
    expect(req.request.body.get("symptoms")).toBeNull();
    req.flush(mockUpload);
  });
});
