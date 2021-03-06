import os.path
from os import listdir
import re
from numpy.distutils.core import setup

def find_version(*paths):
    fname = os.path.join(os.path.dirname(__file__), *paths)
    with open(fname) as fp:
        code = fp.read()
    match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", code, re.M)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version string.")

scripts = ['Scripts/' + i for i in listdir('Scripts/')]

setup(
    name='rfpy',
    version=find_version('rfpy', '__init__.py'),
    description='Python Module for Teleseismic Receiver Functions',
    author='Pascal Audet',
    maintainer='Pascal Audet',
    maintainer_email='pascal.audet@uottawa.ca',
    classifiers=[
         'Development Status :: 3 - Alpha',
         'License :: OSI Approved :: MIT License',
         'Programming Language :: Python :: 3.6',
         'Programming Language :: Python :: 3.7'],
    install_requires = ['numpy', 'obspy', 'stdb', 'cartopy'],
    python_requires =  '>=3.6',
    packages= ['rfpy'],
    scripts=scripts,
    url='')
