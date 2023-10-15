import setuptools


# Function to read the contents of README.md
def readme():
    with open("README.md") as f:
        return f.read()

setuptools.setup(
    name="cogee",
    version="1.0.2",
    packages=setuptools.find_packages(),
    url="https://github.com/samapriya/cogee",
    install_requires=[
        "earthengine-api>=0.1.367",
        "requests>=2.22.0",
        "beautifulsoup4>=4.9.0"
    ],
    license="Apache 2.0",
    long_description=readme(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    author="Samapriya Roy",
    author_email="samapriya.roy@gmail.com",
    description="COG EE flow",
    entry_points={
        "console_scripts": [
            "cogee=cogee.cogee:main"
        ]
    },
)
