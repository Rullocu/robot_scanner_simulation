FROM ros:humble-ros-base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Install basic tools and ROS extras
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    cmake \
    sudo \
    mesa-utils \
    x11-apps \
    python3-pip \
    python3-dev \
    python3-rosdep \
    python3-colcon-common-extensions \
    ros-humble-rviz2 \
    ros-humble-vision-msgs \
    ros-humble-image-transport \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
RUN mkdir -p /ros2_ws/src
WORKDIR /ros2_ws

ENV ROS_DOMAIN_ID=42

# Copy and set entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
