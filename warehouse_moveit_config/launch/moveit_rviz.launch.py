from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_moveit_rviz_launch
from launch_ros.actions import SetParameter


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("ur5e_with_gripper", package_name="warehouse_moveit_config")
        .to_moveit_configs()
    )

    ld = generate_moveit_rviz_launch(moveit_config)

    # Fix clock sync — use Gazebo simulation time
    ld.entities.insert(0, SetParameter(name="use_sim_time", value=True))

    return ld
