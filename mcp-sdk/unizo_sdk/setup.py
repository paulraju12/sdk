from setuptools import setup, find_packages

setup(
    name="unizo-sdk",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "mcp>=0.1.0",  # Adjust version based on your mcp package
        "pydantic>=2.0.0",
        "langchain>=0.2.16",
        "langchain-core>=0.2.38",
        "langchain-openai>=0.1.25",
        "langchain-community>=0.2.16",
        "crewai>=0.30.0",
        "openai>=1.0.0",
        "python-dotenv>=1.0.0"
    ],
    author="Paul",
    author_email="your.email@example.com",
    description="Unizo MCP SDK for ticketing server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/unizo-sdk",
)