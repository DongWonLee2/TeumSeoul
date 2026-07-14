class AppException(Exception):
    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


class ResourceNotFoundError(AppException):
    def __init__(self, detail: str, code: str = "RESOURCE_NOT_FOUND") -> None:
        super().__init__(status_code=404, detail=detail, code=code)

