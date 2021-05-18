package net.gatecat.fpga;

import com.xilinx.rapidwright.device.*;
import jnr.ffi.annotations.In;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.math.BigInteger;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import  java.security.MessageDigest;
import java.util.Base64;

public class tileshapes {
    static long database_size = 0;
    public static class TileInst {
        public int [][] wire_to_node;
        public int [][][] node_wires;

        public TileInst(Tile t) {
            wire_to_node = new int[t.getWireCount()][3];
            node_wires = new int[t.getWireCount()][][];
            for (int i = 0; i < t.getWireCount(); i++) {
                Wire w = new Wire(t, i);
                Node n = w.getNode();

                if (n == null || (w.getBackwardPIPs().size() == 0 && w.getForwardPIPs().size() == 0 && w.getSitePin() == null)) {
                    wire_to_node[i][0] = 0;
                    wire_to_node[i][1] = 0;
                    wire_to_node[i][2] = i;
                } else {
                    Tile tn = n.getTile();
                    wire_to_node[i][0] = tn.getColumn() - t.getColumn();
                    wire_to_node[i][1] = tn.getRow() - t.getRow();
                    wire_to_node[i][2] = n.getWire();
                }

                if (n != null && n.getTile().equals(t) && n.getWire() == i) {
                    Wire [] nw = n.getAllWiresInNode();
                    if (nw != null && nw.length >= 2) {
                        node_wires[i] = new int[nw.length][3];
                        for (int j = 0; j < nw.length; j++) {
                            Tile tw = nw[j].getTile();
                            if (nw[j].getForwardPIPs().isEmpty() && nw[j].getBackwardPIPs().isEmpty() && nw[j].getSitePin() == null && !tw.getName().startsWith("RCLK"))
                                continue;
                            node_wires[i][j][0] = tw.getColumn() - t.getColumn();
                            node_wires[i][j][1] = tw.getRow() - t.getRow();
                            node_wires[i][j][2] = nw[j].getWireIndex();
                        }
                    }
                }
            }
        }

        public long update_node_shapes(HashSet<String> shapes, long node_count) throws NoSuchAlgorithmException {
            MessageDigest md = MessageDigest.getInstance("md5");
            byte[] tempbuf = {0, 0, 0, 0};
            java.util.function.Consumer<Integer> add_int = (Integer x) -> {
                tempbuf[0] = (byte)(x >> 24);
                tempbuf[1] = (byte)(x >> 16);
                tempbuf[2] = (byte)(x >> 8);
                tempbuf[3] = (byte)(x >> 0);
                md.update(tempbuf);
            };
            for (int [][] nw : node_wires) {
                if (nw == null)
                    continue;
                ++node_count;
                add_int.accept(nw.length);
                for (int [] w : nw) {
                    add_int.accept(w[0]);
                    add_int.accept(w[1]);
                    add_int.accept(w[2]);
                }
                byte[] digest = md.digest();
                if(shapes.add(Base64.getEncoder().encodeToString(digest)))
                    database_size += (4 + nw.length * 6);
                md.reset();
            }
            return node_count;
        }

        public String hash() throws NoSuchAlgorithmException {
            MessageDigest md = MessageDigest.getInstance("md5");
            byte[] tempbuf = {0, 0, 0, 0};
            java.util.function.Consumer<Integer> add_int = (Integer x) -> {
                tempbuf[0] = (byte)(x >> 24);
                tempbuf[1] = (byte)(x >> 16);
                tempbuf[2] = (byte)(x >> 8);
                tempbuf[3] = (byte)(x >> 0);
                md.update(tempbuf);
            };
            add_int.accept(wire_to_node.length);
            for (int[] entry : wire_to_node) {
                add_int.accept(entry[0]); // dx
                add_int.accept(entry[1]); // dy
                add_int.accept(entry[2]); // wire index
            }
            add_int.accept(node_wires.length);
            for (int [][] nw : node_wires) {
                if (nw == null) {
                    add_int.accept(0);
                    continue;
                }
                add_int.accept(nw.length);
                for (int [] n : nw) {
                    add_int.accept(n[0]); // dx
                    add_int.accept(n[1]); // dy
                    add_int.accept(n[2]); // wire index
                }
            }
            byte[] digest = md.digest();
            return Base64.getEncoder().encodeToString(digest);
        }
    }

    public static void main(String[] args) throws IOException, NoSuchAlgorithmException {
        Device d = Device.getDevice(args[0]);
        long node_count = 0L;

        HashSet<String> seen_tile_shapes = new HashSet<>();
        HashSet<String> seen_node_shapes = new HashSet<>();
        Collection<Tile> tiles = d.getAllTiles();
        int ti = 0;
        for (Tile t : tiles) {
            if ((ti % 100) == 0)
                System.out.printf("%d/%d\n", (ti+1), tiles.size());
            ++ti;
           TileInst inst = new TileInst(t);
           if (!seen_tile_shapes.contains(inst.hash())) {
               node_count = inst.update_node_shapes(seen_node_shapes, node_count);
               seen_tile_shapes.add(inst.hash());
               database_size += (8 + inst.wire_to_node.length * 6);
               //database_size += inst.node_wires.length * 4;
           }
        }
        System.out.printf("%d tiles, %d tile shapes\n", tiles.size(), seen_tile_shapes.size());
        System.out.printf("%d nontrivial nodes, %d node shapes\n", node_count, seen_node_shapes.size());
        System.out.printf("dedup db size: %dMiB\n", database_size / (1024*1024));
        /*
        FileWriter vf = new FileWriter("/home/david/rapidwright_test/nodes_vu9.txt", false);
        PrintWriter v = new PrintWriter(vf);
        HashSet<Node> seen_nodes = new HashSet<>();
        for (Tile t : d.getAllTiles()) {
            System.out.println(t.getName());
            for (PIP p : t.getPIPs()) {
                Node[] nodes = {p.getStartNode(), p.getEndNode()};
                for (Node n : nodes) {
                    if (seen_nodes.contains(n))
                        continue;
                    var wires = n.getAllWiresInNode();
                    if (wires.length == 0)
                        continue;
                    seen_nodes.add(n);
                    for (Wire w : wires) {
                        v.printf("%d %d %d ", w.getTile().getColumn(), w.getTile().getColumn(), w.getWireIndex());
                    }
                    v.println();

                }
            }
        }
        v.close();
        vf.close();
         */
    }

}
