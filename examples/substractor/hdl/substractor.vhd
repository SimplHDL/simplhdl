library ieee;
use ieee.std_logic_1164.all;
use ieee.std_numeric_unsigned.all;

entity substractor is
    generic(
        WIDTH : integer := 8
    );
    port(
        clk_i : in  std_logic;
        rst_i : in  std_logic;
        a_i   : in  std_logic_vector(WIDTH-1 downto 0);
        b_i   : in  std_logic_vector(WIDTH-1 downto 0);
        sub_o : out std_logic_vector(WIDTH-1 downto 0)
    );
end entity substractor;


architecture rtl of substractor is

begin

    substract: process(clk_i)

    begin
        if posedge
        sub_o <= a_i - b_i;

    end process substract;


end architecture rtl;