from setuptools import setup, find_packages

def readme():
  with open('README.md', 'r') as f:
    return f.read()

setup(
  name='bt_lamp',
  version='1.0.7',
  author='LVettel',
  author_email='larin230@gmail.com',
  description='Controll bluetooth lamp from python',
  long_description=readme(),
  long_description_content_type='text/markdown',
  url='https://github.com/LVettel/bt_lamp',
  packages=find_packages(),
  install_requires=['crcmod>=1.7', 'bleson>=0.1.8'],
  classifiers=[
    'Programming Language :: Python :: 3.9',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent'
  ],
  keywords='bluetooth python lamp',
  project_urls={
    'Documentation': 'https://github.com/LVettel/bt_lamp'
  },
  python_requires='>=3.9'
)
