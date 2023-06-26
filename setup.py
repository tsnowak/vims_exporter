from distutils.core import setup
from pathlib import Path

# resolve README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="vims_exporter",
    version="1.0.0",
    description="Export a VIMS calendar as a .ics file",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tsnowak/vims_exporter",
    author="Theodore Nowak",
    author_email="tednowak814@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    package_dir={"": "src"},
    packages=["vims_exporter"],
    install_requires=[
        "pyqt5",
        "validators",
        "selenium",
        "icalendar",
        "pyinstaller"
    ],
    # include .svg during install
    include_package_data=True,
    # ability to run vims_to_ics in terminal
    entry_points={"console_scripts": ["vims_to_ics = vims_exporter.vims_to_ics:main"]},
)
