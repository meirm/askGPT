from setuptools import setup

setup(
    name='genie',
    package_dir={'':'src'},
    version='0.2.0',
    py_modules=['genie'],
    install_requires=[
        'Click',
        'rich',
        'openai'
    ],
    include_package_data=True,
    include_dirs=[
        'config'
    ],
    entry_points={
        'console_scripts': [
            'genie = genie:cli',
        ],
    },
)
