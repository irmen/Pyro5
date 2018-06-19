import re
import sys
from setuptools import setup


if sys.version_info < (3, 4):
    raise SystemExit("Pyro5 requires Python 3.4 or newer")


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
    description='Remote object communication library, fifth major version',
    long_description=long_description,
    url='https://github.com/irmen/Pyro5',
    author='Irmen de Jong',
    author_email='irmen@razorvine.net',
    keywords=["distributed objects", "RPC", "remote method call", "IPC"],
    license='MIT',

    packages=['Pyro5'],

    install_requires=[
        "serpent>=1.24",
        "msgpack>=0.5.2"
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],

    entry_points={
        'console_scripts': [
            'pyro5-ns = Pyro5.nameserver:main',
            'pyro5-nsc = Pyro5.nsc:main',
            'pyro5-echoserver = Pyro5.utils.echoserver:main',
            'pyro5-check-config = Pyro5.config:dump',
            'pyro5-httpgateway = Pyro5.utils.httpgateway:main'
        ]
    },

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
