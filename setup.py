from setuptools import setup, find_packages

setup(
    name="django-content-interactions",
    url="http://github.com/suselrd/django-content-interactions/",
    author="Susel Ruiz Duran",
    author_email="suselrd@gmail.com",
    version="0.8.1",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    description="Common user-content interactions for Django",
    install_requires=['django>=1.6.1', 'redis>=2.10.3', 'django-redis-cache==1.6.5', 'django-social-graph>=0.3.0'],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Environment :: Web Environment",
        "Framework :: Django",
    ],

)
