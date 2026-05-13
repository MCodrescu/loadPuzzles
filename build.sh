mkdir -p bin
curl -L https://github.com/official-stockfish/Stockfish/releases/download/sf_17/stockfish-ubuntu-x86-64-avx2.tar -o sf.tar
tar -xf sf.tar -C bin --strip-components=1
chmod +x bin/stockfish-ubuntu-x86-64-avx2