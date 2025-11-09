"""
Setup script for queuectl
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

setup(
    name='queuectl',
    version='1.0.0',
    description='CLI-based background job queue system with workers, retries, and DLQ',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/queuectl',
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=[
        'click>=8.0.0',
    ],
    entry_points={
        'console_scripts': [
            'queuectl=queuectl.cli:cli',
        ],
    },
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: System :: Distributed Computing',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='queue job background worker cli task retry dlq',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/queuectl/issues',
        'Source': 'https://github.com/yourusername/queuectl',
    },
)