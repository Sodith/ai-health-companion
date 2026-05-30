import { TestBed } from "@angular/core/testing";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { provideHttpClient } from "@angular/common/http";
import { AnalysisService } from "./analysis.service";
import { environment } from "../../../environments/environment";
const BASE = `${environment.apiUrl}/analysis`;
const mockAnalysis = { analysis_id: 10, prescription_id: 1, analysis_status: "completed", disease_detected: "Hypertension", doctor_advice: ["Reduce salt"], lifestyle_changes: ["Exercise"], medicines: [], disclaimer: "AI is not medical advice.", created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
const mockResponse = { success: true, status_code: 201, message: "OK", data: mockAnalysis, error: null };
describe("AnalysisService", () => {
  let service: AnalysisService;
  let httpMock: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [AnalysisService, provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(AnalysisService);
    httpMock = TestBed.inject(HttpTestingController);
  });
  afterEach(() => httpMock.verify());
  it("should be created", () => { expect(service).toBeTruthy(); });
  it("should POST to /analysis/:id to trigger analysis", () => {
    let result: any;
    service.trigger(1).subscribe(r => (result = r));
    const req = httpMock.expectOne(`${BASE}/1`);
    expect(req.request.method).toBe("POST");
    req.flush(mockResponse);
    expect(result.success).toBe(true);
    expect(result.data.disease_detected).toBe("Hypertension");
    expect(result.data.analysis_status).toBe("completed");
  });
  it("should GET from /analysis/:id to retrieve existing analysis", () => {
    let result: any;
    service.getByPrescriptionId(1).subscribe(r => (result = r));
    const req = httpMock.expectOne(`${BASE}/1`);
    expect(req.request.method).toBe("GET");
    req.flush({ ...mockResponse, status_code: 200 });
    expect(result.data.medicines).toEqual([]);
    expect(result.data.doctor_advice.length).toBe(1);
  });
});
