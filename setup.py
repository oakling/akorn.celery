from setuptools import setup, find_packages
import os

version = open(os.path.join("akorn", "celery", "version.txt")).read().strip()

setup(name='akorn.celery',
      version=version,
      description="",
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='Akorn',
      author='',
      author_email='',
      url='',
      license='',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['akorn'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
      ],
      entry_points="""
          [console_scripts]
          run_schedule = akorn.celery.scripts.run_schedule:main
          run_all_schedule = akorn.celery.scripts.run_all_schedule:main
      """,
)
