# Intel IPs

The quartus flow handles IPs by copying them the build folder. This in done to
prevent Quartus from poluting the source tree. The Quartus flow support three
ways of working with IPs.

1. A single `.ip` file. Quartus flow will copy the `.ip` file to the build
   directory and generate the IP source.

2. An `.ip` file and a directory with generated IP source. The Quartus flow will
   copy both the `.ip` file and the directory to the build folder.

3. A single `.ipx` file. The `.ipx` file is a zip archive containing the `.ip`
   file and the directory with the generated source. The Quartus flow will
   unzip the content in the build folder.

> **What is an `.ipx` zip archive?**
>
> An `.ipx` file is an ordinary zip archive containing the `.ip` file and
> the directory of the IP's generated source. The benefits by archiving the IP
> source is that it is easier to manage. It can also be added to Git LFS to
> prevent the Git repository size to *explode*.
