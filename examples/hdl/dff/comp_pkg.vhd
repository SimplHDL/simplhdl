library ieee;
use ieee.std_logic_1164.all;


package comp_pkg is

    component dff
        port (
            c : in  std_logic;
            d : in  std_logic;
            q : out std_logic
        );
    end component;

end package;
