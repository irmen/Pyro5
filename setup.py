import re
from setuptools import setup


with open("Readme.rst", encoding="utf-8") as f:
    long_description = f.read()

with open("Pyro5/__init__.py") as f:
    # extract the version string
    version_line = next(line for line in f if line.startswith("__version__"))
    pyro_version = re.match("__version__ ?= ?['\"](.+)['\"]", version_line).group(1)
    if not pyro_version:
        raise ValueError("cannot determine pyro version")
    print("Pyro version =", pyro_version)

setup(
    name='Pyro5',
    version=pyro_version,
    description='Remote object communication library, fifth incarnation',
    long_description=long_description,
    url='https://github.com/irmen/Pyro5',
    author='Irmen de Jong',
    author_email='irmen@razorvine.net',
    keywords=["distributed objects", "RPC", "remote method call", "IPC"],
    license='MIT',

    packages=['Pyro5'],

    install_requires=[
        "serpent>=1.23",
        "msgpack-python>=0.4.6"
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Natural Language :: Dutch",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Object Brokering",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Networking"
    ],

)
