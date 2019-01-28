from setuptools import setup

setup(
    name='bpchain',
    include_package_data=True,
    install_requires=[
        'flask',
        'requests',
        'zmq',
        'base58',
        'ecdsa',
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)
