from setuptools import setup, find_packages
from src.simple_parser import __version__


setup(
    name='SimplHDL-simple_parser',
    description='A simple parser plugin for SimplHDL',
    version=__version__,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    entry_points={
        'simplhdl.plugins': [
            'parser=simple_parser'],
    },
    install_requires=[
        'simplhdl'
    ],
)
