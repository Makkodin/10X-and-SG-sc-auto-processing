from setuptools import setup, find_packages

setup(
    name='sc-processing',
    version='1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'sc-processing=main.run:main',
        ],
    },
    install_requires=[
    ],
)