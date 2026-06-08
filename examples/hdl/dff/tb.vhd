library ieee;
use ieee.std_logic_1164.all;

use work.comp_pkg.all;


entity tb is
end entity;

architecture sim of tb is

   signal c : std_logic;
   signal d : std_logic;
   signal q : std_logic;

begin

   dff_inst: COMPONENT dff
    port map(
       c => c,
       d => d,
       q => q
   );

end architecture sim;
