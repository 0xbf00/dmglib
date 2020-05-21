import setuptools

with open("README.md", "r") as fh:
    long_desc = fh.read()

setuptools.setup(
      name='dmglib',
      version='0.9.1',
      description='Work with macOS DMG disk images',
      long_description=long_desc,
      long_description_content_type="text/markdown",
      author='Jakob Rieck',
      author_email='jakobrieck+pypi@gmail.com',
      url='https://github.com/0xbf00/dmglib',
      license='MIT License',
      sys_platform=['darwin'],
      package_dir={'': 'src'},
      py_modules=['dmglib'],
      classifiers = [
		'Programming Language :: Python :: 3.7',
		'Operating System :: MacOS',
		'Development Status :: 5 - Production/Stable',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: MIT License'
	  ],
      provides=['dmglib']
)