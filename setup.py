import pathlib
import re

from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent.resolve()

# Read version from __init__.py (single source of truth).
_init_file = here / "src" / "cynthium" / "__init__.py"
_match = re.search(r'__version__\s*=\s*"([^"]+)"', _init_file.read_text())
version = _match.group(1) if _match else "0.0a4"

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="cynthium",
    version=version,
    # https://packaging.python.org/specifications/core-metadata/#summary
    description="A tool for simulating rover traverses on the Moon.",
    # This field corresponds to the "Description-Content-Type" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#description-content-type-optional
    long_description_content_type="text/markdown",  # Optional (see note above)
    # This field corresponds to the "Home-Page" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#home-page-optional
    url="https://github.com/osh3276/cynthium",  # Optional
    author="Oliver Huang",  # Optional
    author_email="oli.huang@mail.utoronto.ca",  # Optional
    packages=find_packages(where="src"),  # Required
    # Specify which Python versions you support. In contrast to the
    # 'Programming Language' classifiers above, 'pip install' will check this
    # and refuse to install the project if the version does not match. See
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires
    python_requires=">=3.12",
    # This field lists other packages that your project depends on to run.
    # Any package you put here will be installed by pip when your project is
    # installed, so they must be valid existing projects.
    #
    # If there are data files included in your packages that need to be
    # installed, specify them here.
    # Entry points. The following would provide a command called `sample` which
    # executes the function `main` from this package when invoked:
    entry_points={  # Optional
        "console_scripts": [
            "cynthium=cynthium.app.main:main",
        ],
    },
    #
    # project_urls={  # Optional
    #     "Bug Reports": "https://github.com/pypa/sampleproject/issues",
    #     "Funding": "https://donate.pypi.org",
    #     "Say Thanks!": "http://saythanks.io/to/example",
    #     "Source": "https://github.com/pypa/sampleproject/",
    # },
)
