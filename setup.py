from setuptools import setup

setup(
    name='askGPT',
    url='https://www.github.com/meirm/askGPT.git',
    author='Meir Michanie',
    author_email='meirm@riunx.com',
    readme='README.md',
    description='A simple CLI for OpenAI GPT-3',
    license='MIT',
    package_dir={'':'src'},
    version='0.2.1',
    py_modules=['askGPT'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
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
            'askGPT = askGPT:cli',
        ],
    },
)
