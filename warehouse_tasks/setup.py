from setuptools import setup

package_name = 'warehouse_tasks'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dong',
    maintainer_email='you@email.com',
    description='Pick and place task nodes',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
        ],
    },
)