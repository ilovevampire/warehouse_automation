import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue 

def launch_setup(context, *args, **kwargs):

    tf_prefix   = LaunchConfiguration("tf_prefix")
    launch_rviz = LaunchConfiguration("launch_rviz")

    warehouse_desc_pkg = FindPackageShare("warehouse_description")
    ur_description_pkg = FindPackageShare("ur_description")

    controllers_file = PathJoinSubstitution(
        [warehouse_desc_pkg, "config", "ros2_controllers.yaml"]
    )
    description_file = PathJoinSubstitution(
        [warehouse_desc_pkg, "urdf", "ur5e_with_gripper.urdf.xacro"]
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ", description_file,
            " name:=ur5e",
            " tf_prefix:=",        tf_prefix,
            " simulation_controllers:=", controllers_file,
        ]
    )
    robot_description = {"robot_description": ParameterValue(robot_description_content, value_type=str)}

    # --- Nodes ---

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[{"use_sim_time": True}, robot_description],
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare("ros_gz_sim"), "/launch/gz_sim.launch.py"]
        ),
        launch_arguments={
            "gz_args": "-r -v 4 --physics-engine gz-physics-bullet-featherstone-plugin empty.sdf"
        }.items(),
    )

    gz_spawn = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-string", robot_description_content,
            "-name",   "ur5e_with_gripper",
            "-allow_renaming", "true",
        ],
    )

    gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c", "/controller_manager"],
    )

    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_trajectory_controller", "-c", "/controller_manager"],
    )

    gripper_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["robotiq_gripper_controller", "-c", "/controller_manager"],
    )

    # RGB + Depth image bridge (gz -> ROS image topics)
    camera_image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=[
            '/camera/image',
            '/camera/depth_image',
        ],
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # PointCloud2 + CameraInfo bridge
    camera_info_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    delay_controllers_after_jsb = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[arm_controller_spawner, gripper_controller_spawner],
        )
    )

    rviz_config = PathJoinSubstitution(
        [ur_description_pkg, "rviz", "view_robot.rviz"]
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config],
        parameters=[{"use_sim_time": True}],
    )

    delay_rviz_after_jsb = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[rviz_node],
        )
    )

    return [
        robot_state_publisher,
        gz_sim,
        gz_spawn,
        gz_bridge,
        camera_image_bridge,        # <-- added camera
        camera_info_bridge,         # <-- add camera 
        joint_state_broadcaster_spawner,
        delay_controllers_after_jsb,
        delay_rviz_after_jsb,
    ]


def generate_launch_description():

    # Set GZ resource path so Gazebo finds robotiq + ur meshes
    set_gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=os.path.expanduser('~') + '/warehouse_ws/install/robotiq_description/share:'
            + os.path.expanduser('~') + '/warehouse_ws/install/ur_description/share'
    )

    return LaunchDescription([
        set_gz_resource_path,
        DeclareLaunchArgument("tf_prefix",   default_value="",     description="TF prefix"),
        DeclareLaunchArgument("launch_rviz", default_value="true", description="Launch RViz"),
        OpaqueFunction(function=launch_setup),
    ])