from setuptools import setup

setup(
    name='dockstrap',
    version='0.1',
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
