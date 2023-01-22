from setuptools import setup

setup(
    name='genie',
    version='0.1.0',
    py_modules=['genie'],
    install_requires=[
        'Click',
        'rich',
        'openai'
    ],
    entry_points={
        'console_scripts': [
            'genie = genie:cli',
        ],
    },
)
