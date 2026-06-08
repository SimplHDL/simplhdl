library ieee;
use ieee.std_logic_1164.all;


entity dff is
   port (
      c : in  std_logic;
      d : in  std_logic;
      q : out std_logic
   );
end entity;


architecture rtl of dff is

begin

   process(c)
   begin
      if rising_edge(c) then
         q <= d;
      end if;
   end process;

end architecture;
