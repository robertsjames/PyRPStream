import setuptools

with open('requirements.txt') as f:
    requires = [x.strip() for x in f.readlines()]

setuptools.setup(
    name='PyRPStream',
    version='0.10.3',
    author='Robert James, Fiona Alder',
    author_email='robert.james.19@ucl.ac.uk',
    url='https://github.com/robertsjames/PyRPStream',
    python_requires=">=3.8",
    install_requires=requires,
    packages=setuptools.find_packages())
