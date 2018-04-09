#!/usr/bin/python
"""mbspbs10pc setup script."""

from setuptools import setup

# Package Version
from mbspbs10pc import __version__ as version

setup(
    name='mbspbs10pc',
    version=version,

    description=("MBS-PBS 10% dataset utilities"),
    long_description=open('README.md').read(),
    author='Samuele Fiorini, Farshid Hajati, Federico Girosi',
    author_email='samuele.fiorini@dibris.unige.it',
    maintainer='Samuele Fiorini',
    maintainer_email='samuele.fiorini@dibris.unige.it',
    url='https://github.com/samuelefiorini/mbspbs10pc',
    download_url='https://github.com/samuelefiorini/mbspbs10pc/tarball/' + version,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'License :: OSI Approved :: BSD License',
        'Topic :: Software Development',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Operating System :: MacOS'
    ],
    license='FreeBSD',

    packages=['mbspbs10pc', 'notebook'],
    install_requires=['numpy (>=1.14.2)',
                      'scikit-learn (>=0.19)',
                      'pandas (>=0.22.0)',
                      'joblib (>=0.11)',
                      'keras (>=2.1.5)',
                      'tensorflow (>=1.6.0)',
                      'matplotlib (>=2.1.1)'],
    scripts=['scripts/assign_labels.py', 'scripts/cross_validate.py',
             'scripts/extract_sequences.py',
             'scripts/get_population_of_interest.py',
             'scripts/matching_step1.py',
             'scripts/matching_step2.R',
             'scripts/single_train.py'],
)
