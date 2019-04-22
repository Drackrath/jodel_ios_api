from setuptools import setup, find_packages
import os

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    long_description = f.read()

setup(name='jodel_ios_api',
      version='1.0.2',
      description='Unoffical Python Interface to the Jodel API (based on iOS)',
      long_description=long_description,
      url='https://github.com/marbink/jodel_ios_api',
      author='marbink',
      author_email='github@marbink.eu',
      license='MIT',
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Message Boards',
        'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      keywords='jodel',
      package_dir={'': 'src'},
      install_requires=['requests', 'future', 'simplejson'],
      packages=find_packages('src'),
      zip_safe=False)
