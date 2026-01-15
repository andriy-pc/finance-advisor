def extract_file_extension(filename: str) -> str:
    return filename.split(".")[-1].lower() if "." in filename else ""
