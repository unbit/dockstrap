from setuptools import setup

setup(
    name='dockstrap',
    version='0.2',
    description='Like debootstrap but uses docker registry',
    author='Unbit',
    author_email='info@unbit.it',
    license='MIT',
    py_modules=['dockstrap'],
    install_requires=[
        'requests',
        'Click',
    ],
    entry_points='''
        [console_scripts]
        dockstrap=dockstrap:dockstrap_run
    ''',
)
