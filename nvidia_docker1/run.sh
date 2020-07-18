#!/bin/bash

image_name="image_to_gravity"
root_path=$(pwd)

xhost +
nvidia-docker run -it --rm \
	--env="DISPLAY" \
	--env="QT_X11_NO_MITSHM=1" \
	--volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
	--net=host \
	-v $root_path/../dataset:/home/$image_name/dataset \
	-v $root_path/../weights:/home/$image_name/weights \
	-v $root_path/../graph:/home/$image_name/graph \
	-v $root_path/../mle:/home/$image_name/mle \
	$image_name:nvidia_docker1
