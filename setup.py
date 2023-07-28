from setuptools import setup, find_packages
from src.simplhdl import __version__, __author__, __email__


with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='SimplHDL',
    description='A framework for simulating and implementing HDL designs',
    long_description=long_description,
    author=__author__,
    author_email=__email__,
    version=__version__,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    entry_points={
        'console_scripts': ['simpl=simplhdl.__main__:main'],
    },
    install_requires=[
        'pyEDAA.ProjectModel',
        'pyyaml',
        'types-PyYAML',
        'edalize'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
)
