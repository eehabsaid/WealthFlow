"""
Certificate balance-deduction tests, split by class (200-line rule):
  - test_service.py     — CertificateBalanceDeductionServiceTest (model-level deduction/reversal logic)
  - test_api_errors.py  — CertificateBalanceDeductionApiErrorTest (view-layer JSON 400 error handling)

Both sibling files keep the test_ prefix so Django's test discovery
(manage.py test) finds them the same way it found the original flat file.
"""
