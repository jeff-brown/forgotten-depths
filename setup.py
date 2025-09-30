"""Setup script for Forgotten Depths MUD."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "A Python-based Multi-User Dungeon (MUD) game"

# Read requirements
def read_requirements(filename):
    """Read requirements from file."""
    req_path = Path(__file__).parent / "requirements" / filename
    if req_path.exists():
        with open(req_path, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#") and not line.startswith("-r")]
    return []

setup(
    name="forgotten-depths",
    version="0.1.0",
    description="A Python-based Multi-User Dungeon (MUD) game",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/forgotten-depths",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=read_requirements("base.txt"),
    extras_require={
        "dev": read_requirements("dev.txt"),
        "test": read_requirements("test.txt"),
        "web": ["Flask>=2.3.0", "Flask-SocketIO>=5.3.0"],
    },
    entry_points={
        "console_scripts": [
            "forgotten-depths=main:main",
            "fd-server=scripts.start_server:main",
            "fd-admin=scripts.admin_tools:main",
            "fd-reset-db=scripts.reset_database:main",
            "fd-create-world=scripts.create_world:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment",
        "Topic :: Games/Entertainment :: Multi-User Dungeons (MUD)",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="mud game multiplayer text adventure rpg",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/forgotten-depths/issues",
        "Source": "https://github.com/yourusername/forgotten-depths",
        "Documentation": "https://github.com/yourusername/forgotten-depths/blob/main/docs/setup.md",
    },
    include_package_data=True,
    package_data={
        "": ["data/**/*.json", "data/**/*.yaml", "config/*.yaml"],
    },
    zip_safe=False,
)