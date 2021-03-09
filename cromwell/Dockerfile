FROM broadinstitute/cromwell:58
ENV JAVA_OPTS="-Dconfig.file=/mnt/google.conf"
COPY ./google.conf /mnt/google.conf
CMD ["java", "-Dconfig.file=/mnt/google.conf", "run", "/mnt/data/hello.wdl", "-i", "/mnt/data/hello.inputs"]
