
On a fresh VM:
```
$ apt update
```

Install docker and start the service
```
$ apt install docker.io
$ systemctl start docker && systemctl enable docker
```

Install Python dependencies
```
$ apt install python-pip
$ pip3 install uvicorn --no-deps click h11 asgineer
```

