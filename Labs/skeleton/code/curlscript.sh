for i in `seq 1 60`; do 
    curl -d "entry=Hello${i}" -X POST 10.1.0.1:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.2:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.3:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.4:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.5:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.6:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.7:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.8:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.9:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.10:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.11:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.12:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.13:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.14:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.15:80/board
    curl -d "entry=Hello${i}" -X POST 10.1.0.16:80/board
done

#for i in `seq 1 60`; do 
#    curl -d "entry=Hello${i}" -X POST 10.1.0.2:80/board
#done

#for i in `seq 1 60`; do 
#    curl -d "entry=Hello${i}" -X POST 10.1.0.3:80/board
#done

#for i in `seq 1 60`; do 
#    curl -d "entry=Hello${i}" -X POST 10.1.0.4:80/board
#done
