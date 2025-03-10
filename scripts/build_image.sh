#!/bin/bash -e
set -euxo pipefail

source ../project_config.sh

if [[ -z "$NAME" ]]; then
    echo "Please edit project_config.sh and specify a NAME".
    exit 1
fi

VERSION=$(git describe | sed 's#/v#:#g')

if [[ ! "$VERSION" =~ ^$NAME:.* ]]; then
    echo "Last tag did not conform to naming spec $NAME:1.1.1"
    exit 1
fi

echo "Building image $VERSION"
docker build --ulimit nofile=262144:262144 --tag $VERSION .

docker tag $VERSION diadem.azurecr.io/$VERSION
echo "You can now push this image by logging in to azure with the supplied info by NM"
echo "az login"
echo "and then doing"
echo "az acr login -n diadem"
echo "and then push the image with"
echo "docker push diadem.azurecr.io/$VERSION"
