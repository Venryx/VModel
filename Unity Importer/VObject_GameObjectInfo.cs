using UnityEngine;

public class VObject_GameObjectInfo : MonoBehaviour
{
	public bool anchorToTerrain;
	public bool anchorVertexesToTerrain;
	//public VVector3? gateGrate_openPosition;
	public VVector3 gateGrate_openPosition = VVector3.Null; // normal/non-nullable version needed to be recognized (and therefore copied) when GameObject tree is copied
}