import discord
from src.hotconfig import get_channel


async def require_channel(
    interaction: discord.Interaction, command_name: str, ephemeral: bool = True
) -> bool:
    required_ch = await get_channel(command_name)
    if required_ch == 0 or interaction.channel_id == required_ch:
        return True
    await interaction.response.send_message(
        f"🔴 不可在未授權之頻道使用該指令\n請前往 <#{required_ch}> 使用此功能",
        ephemeral=ephemeral,
    )
    return False
