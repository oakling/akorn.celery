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
      scripts=['scripts/run_all_schedule.py', 'scripts/run_schedule.py'],
      entry_points="""
          [console_scripts]
          run_schedule = akorn.celery.bin.run_schedule:main
          run_all_schedule = akorn.celery.bin.run_all_schedule:main
      """,
)
