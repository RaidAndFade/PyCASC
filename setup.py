import setuptools
with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='PyCASC',  
    version='0.1.0',
    author="raidandfade",
    author_email="business@gocode.it",
    description="Pure Python CASC file structure reader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/raidandfade/pycasc",
    packages=["PyCASC","PyCASC.utils","PyCASC.rootfiles"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "requests==2.21.0",
        "salsa20==0.3.0"
    ]
 )