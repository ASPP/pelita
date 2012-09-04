from setuptools import setup

setup(name='pelita',
      version='0.1.1',
      description='Actor-based Toolkit for Interactive Language Education in Python',
      author='Valentin Haenel and Rike-Benjamin Schuppner and others',
      author_email='',
      url='http://aspp.github.com/pelita',
      license = "2-clause BSD",
      packages=['pelita', 
                'pelita.messaging', 
                'pelita.messaging.remote', 
                'pelita.ui',
                'pelita.utils', 
                'pelita.compat',
                ],
      scripts=['pelitagame'],
      install_requires=[
          'pyzmq >= 2.1.9'
        ],
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: BSD License',
          'Topic :: Scientific/Engineering :: Artificial Intelligence'
      ]
      
     )

