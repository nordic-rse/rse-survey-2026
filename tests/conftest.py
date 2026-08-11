def pytest_configure(config):
    config.addinivalue_line("markers", "hf: needs Hugging Face models / GPU")
