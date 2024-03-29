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
    package_data={
        'simplhdl.resources.templates.quartus': ['*'],
        'simplhdl.resources.templates.vivado': ['*'],
        'simplhdl.resources.templates.questasim': ['*'],
        'simplhdl.resources.templates.vcs': ['*'],
        'simplhdl.resources.templates.xsim': ['*'],
        'simplhdl.resources.templates.rivierapro': ['*'],
    },
    include_package_data=True,
    entry_points={
        'console_scripts': ['simpl=simplhdl.__main__:main'],
    },
    install_requires=[
        'importlib-resources;python_version<"3.9"',
        'pySVModel==0.3.5',
        'pyEDAA.ProjectModel==0.4.3',
        'pyyaml',
        'types-PyYAML',
        'edalize',
        'argcomplete',
        'jinja2',
        'GitPython',
    ],
    classifiers=[
        'Development Status :: 3 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License'
        'Operating System :: OS Independent',
    ],
)
