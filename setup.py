from setuptools import setup, find_packages

setup(
    name='simulator',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[],  # No external dependencies for built-in modules
    author='Your Name',
    author_email='your.email@example.com',
    description='A flexible job simulation framework',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/simulator',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
)