from setuptools import setup, find_packages

setup(
    name="sledge-browser",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'PyQt6>=6.4.0',
        'PyQt6-WebEngine>=6.4.0',
        'cryptography>=39.0.0',
    ],
    entry_points={
        'console_scripts': [
            'sledge=sledge.browser:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A powerful, secure web browser with advanced tab management",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/sledge",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    include_package_data=True,
) 