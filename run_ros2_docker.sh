#!/bin/bash
set -e

# Configuration
IMAGE_NAME="ros2_ws"
CONTAINER_NAME="ros2_container"

# Function to print colored output
print_colored() {
    echo -e "\e[1;34m$1\e[0m"
}

# Check if image exists, build if it doesn't
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
    print_colored "Building Docker image: $IMAGE_NAME"

    TMP_DIR=$(mktemp -d)
    cp Dockerfile $TMP_DIR/
    cp entrypoint.sh $TMP_DIR/

    docker build -f Dockerfile -t $IMAGE_NAME $TMP_DIR

    rm -rf $TMP_DIR
else
    print_colored "Docker image $IMAGE_NAME already exists"
fi

# Stop and remove any existing container with the same name
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    print_colored "Stopping existing container: $CONTAINER_NAME"
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

if [ "$(docker ps -aq -f status=exited -f name=$CONTAINER_NAME)" ]; then
    print_colored "Removing stopped container: $CONTAINER_NAME"
    docker rm $CONTAINER_NAME
fi

# Create workspace directories if they don't exist
print_colored "Ensuring workspace directories exist"
mkdir -p "$(pwd)/src"
mkdir -p "$(pwd)/build"
mkdir -p "$(pwd)/install"
mkdir -p "$(pwd)/log"

# Allow X server connections from local containers
print_colored "Setting up X server permissions"
xhost +local:docker

# Run the container
docker run -it --rm \
    --name $CONTAINER_NAME \
    --network=host \
    --privileged \
    -e DISPLAY=$DISPLAY \
    -e ROS_DOMAIN_ID=42 \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
    -v "$(pwd)/src:/ros2_ws/src" \
    -v "$(pwd)/build:/ros2_ws/build" \
    -v "$(pwd)/install:/ros2_ws/install" \
    -v "$(pwd)/log:/ros2_ws/log" \
    -v /dev:/dev \
    $IMAGE_NAME "$@"

# Clean up X server permissions when done
print_colored "Cleaning up X server permissions"
xhost -local:docker
print_colored "Container execution completed"
