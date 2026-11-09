// What a failed call looks like to the UI, whichever transport (browser fetch or VS Code host) produced it.
export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}
