from setuptools import setup, find_packages

setup(
    name='lighter_api_tools',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'web3',
        'requests'
    ],
    author='Your Name',
    author_email='your.email@example.com',
    description='A Python SDK for interacting with Lighter DEX API',
    url='https://github.com/yourusername/lighter-api-tools',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
