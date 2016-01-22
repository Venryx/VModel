#if UNITY_EDITOR
using UnityEditor.VersionControl;
using UnityEditor;
#endif

using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;
using VTree;
using VTree.BiomeDefenseN;
using VTree.BiomeDefenseN.ObjectsN;
using System.Collections.Generic;
using Object = UnityEngine.Object;

public class VModelImporter
{
	public class ModelInfo
	{
		public DirectoryInfo folder;
		public VDFNode rootNode;
		public Dictionary<string, VDFNode> objNodes;
		public Dictionary<string, Texture2D> textureCache = new Dictionary<string, Texture2D>();
		public GameObject rootObj;
	}

	// see VDFAndJSON.cs for the vdf-to-json-prop-name-map
	public static GameObject LoadModel(DirectoryInfo folder, string modelFileName, bool setModelPivotToTheModelCenter, TimeInfoNode timeInfo) // folder argument currently needed to apply textures
	{
		if (!BD.main.settings.loadModels)
			return new GameObject(folder.Name);
		TimeInfoNode timeL1;
		TimeInfoNode timeL2;

		// flags, set here in code
		var allowLoadCacheL2 = !Application.isEditor; // disallow loading CacheL2 in editor, since creating CacheL3 (which happens automatically when playing in editor) requires that we load from CacheL1
		//var allowSaveCacheL2 = !Application.isEditor; // disallow saving of CacheL2 in editor, since while in-editor there's a better cache usable (CacheL3), and CacheL2 takes up time and space
		var allowSaveCacheL2 = false; // disallow saving of CacheL2 completely, since we're not near release (i.e. a point where CacheL2 is useful for anyone)

		var modelsObj = BD.main.objects._gameObject.GetChild("Models");
		var cacheL1Exists = folder.GetFile("CacheL1/Model.vmodel.json").Exists;
		var cacheL2Exists = folder.GetFile("CacheL2/Model.assetbundle").Exists;
		//var cacheL3Exists = folder.GetFolder("CacheL3").Exists && VResources.Load<GameObject>("CacheL3_Objects/" + folder.Name);
		//var cacheL3Exists = folder.GetFolder("CacheL3").Exists && Application.isEditor && FileManager.unityRoot.GetFile("Assets/BiomeDefense/Objects/Models/CacheL3/" + folder.Name + ".prefab").Exists;
		var cacheL3Exists = folder.GetFolder("CacheL3").Exists && (modelsObj.GetChild("Static_Manual/" + folder.Name) || modelsObj.GetChild("Static_Generated/" + folder.Name));
		//var cacheComplete = cacheL1Exists && cacheL2Exists && cacheL3Exists;

		GameObject model = null;

		// load model
		// ==========

		VDFNode cacheL1_rootNode = null;
		JObject cacheL1_rootNode_json = null;
		GameObject cacheL2AndL3_asset = null;
		if (cacheL1Exists && (!cacheL2Exists || !allowLoadCacheL2) && !cacheL3Exists) // if CacheL1 exists, and none later, load it
		{
			timeL1 = timeInfo.AddChild("CacheL1 - load data");

			/*VDebug.Block(false);
			rootNode_json = JObject.Parse(File.ReadAllText(folder.GetFile("CacheL1/Model.vmodel.json").FullName));
			timeInfo_treeLoading.AddChild("JSON load", VDebug.Block(false));
			rootNode = VDFAndJSON.ToVDFNode(rootNode_json);
			timeInfo_treeLoading.AddChild("VDF load (from JSON)", VDebug.Block(false));*/
			timeL2 = timeL1.AddChild("Load JSON");
			cacheL1_rootNode_json = JObject.Parse(File.ReadAllText(folder.GetFile("CacheL1/Model.vmodel.json").FullName));
			timeL2.NotifyFinished();
			timeL2 = timeL1.AddChild("Load VDF (from JSON)");
			cacheL1_rootNode = VDFAndJSON.ToVDFNode(cacheL1_rootNode_json);
			timeL2.NotifyFinished();

			timeL1.NotifyFinished();

			timeL1 = timeInfo.AddChild("CacheL1 - load model");
			model = LoadModel_FromCacheL1(folder, cacheL1_rootNode, setModelPivotToTheModelCenter, timeL1);
			timeL1.NotifyFinished();
		}
		else if (cacheL2Exists && allowLoadCacheL2 && !cacheL3Exists) // if CacheL2 exists, and none later, load it
		{
			timeL1 = timeInfo.AddChild("CacheL2 - load model");

			var assetBundle = AssetBundle.CreateFromFile(folder.GetFile("CacheL2/Model.assetbundle").FullName);
			foreach (string path in assetBundle.GetAllAssetNames())
			{
				string pathCopy = path;
				if (path.EndsWith(".prefab") || path.EndsWith(".spm"))
				{
					//var request = assetBundle.LoadAssetWithSubAssetsAsync<GameObject>(path);
					/*var timeAtLoadAsyncStart = Time.realtimeSinceStartup;
					AssetBundleRequest request = null;
					VCoroutine.Start(VCoroutine.WaitForSeconds(10444), VCoroutine.Do(()=>request = assetBundle.LoadAssetWithSubAssetsAsync<GameObject>(pathCopy)), VCoroutine.WaitTill(()=>request.isDone), VCoroutine.Do(()=>
					{
						VDebug.Log("Done loading model for object '" + folder.Name + "'. Time since load-async start: " + ((Time.realtimeSinceStartup - timeAtLoadAsyncStart) * 1000) + "ms");
					}));*/

					//var objAndSubObjects = assetBundle.LoadAssetWithSubAssets(folder.Name);
					//var result_final = (GameObject)objAndSubObjects[0];
					model = (GameObject)assetBundle.mainAsset;
					//model = V.Clone((GameObject)assetBundle.mainAsset);
					//result_final.transform.SetParent(BD.main._gameObject.GetChild("#General/VModelImporter_TempHolder").transform, false);

					timeL1.NotifyFinished();
				}
			}
			//return new GameObject(folder.Name);
		}
		else if (cacheL3Exists) // if CacheL3 exists, load it
		{
			timeL1 = timeInfo.AddChild("CacheL3 - load model");
			//cacheL2AndL3_asset = V.Clone(VResources.Load<GameObject>("CacheL3_Objects/" + folder.Name));
			//model = cacheL2AndL3_asset;
			model = modelsObj.GetChild("Static_Manual/" + folder.Name) ?? modelsObj.GetChild("Static_Generated/" + folder.Name);
			timeL1.NotifyFinished();
		}

		// maybe todo: make this always create non-readable textures within the assets and asset-bundles it creates (to have them use less memory)
		//VAssetProcessor_RuntimeData.makeTexturesReadable = true;

		// for any cache level later than those currently existing, try to create it
		if (!cacheL1Exists && !cacheL2Exists && !cacheL3Exists && folder.GetFile(modelFileName).Exists) // if CacheL1-and-later don't exist, and we can create CacheL1, do so (as well as load the model from this new cache data)
		{
			timeL1 = timeInfo.AddChild("CacheL1 - create data");

			var modelVDF = File.ReadAllText(folder.GetFile(modelFileName).FullName);

			/*var modelVDF_json = VDFAndJSON.ToJSON(modelVDF.Replace("\r", ""));
			cacheL1_rootNode_json = JObject.Parse(modelVDF_json);*/

			cacheL1_rootNode = VDFLoader.ToVDFNode(modelVDF);
			cacheL1_rootNode_json = (JObject)VDFAndJSON.ToJToken(cacheL1_rootNode);
			VDFAndJSON.ProcessJSONTree(cacheL1_rootNode_json);

			timeL1.NotifyFinished();

			timeL1 = timeInfo.AddChild("CacheL1 - save data");
			File.WriteAllText(folder.GetFile("CacheL1/Model.vmodel.json").CreateFolders().FullName, cacheL1_rootNode_json.ToString(Formatting.None));
			timeL1.NotifyFinished();

			timeL1 = timeInfo.AddChild("CacheL1 - load model");
			model = LoadModel_FromCacheL1(folder, cacheL1_rootNode, setModelPivotToTheModelCenter, timeL1);
			timeL1.NotifyFinished();
		}
		#if UNITY_EDITOR
		if (!cacheL2Exists && allowSaveCacheL2 && !cacheL3Exists) // if CacheL2-and-later don't exist, and we can create CacheL2, do so
		{
			
			timeL1 = timeInfo.AddChild("CacheL2 - create and save");

			timeL2 = timeL1.AddChild("Create asset");
			cacheL2AndL3_asset = CreateAssetForModel(model);
			//cacheL2AndL3_asset = CreateAssetForModel(V.Clone(model));
			timeL2.NotifyFinished();

			timeL2 = timeL1.AddChild("Create bundle");
			// create bundle, and move it
			var assetBundlePath = "Assets/BiomeDefense/Objects/Models/CacheL2/" + folder.Name + ".assetbundle";
			//AssetDatabase.DeleteAsset(assetBundlePath);
			BuildPipeline.BuildAssetBundle(cacheL2AndL3_asset, new[] {cacheL2AndL3_asset}, assetBundlePath, BuildAssetBundleOptions.UncompressedAssetBundle | BuildAssetBundleOptions.CollectDependencies, BuildTarget.StandaloneWindows);
			//BuildPipeline.BuildAssetBundle(mainAsset, assets.ToArray(), assetBundlePath, BuildAssetBundleOptions.UncompressedAssetBundle | BuildAssetBundleOptions.CollectDependencies, BuildTarget.StandaloneWindows);
			FileManager.root.Parent.GetFile(assetBundlePath).MoveTo(folder.GetFile("CacheL2/Model.assetbundle").CreateFolders().FullName);
			timeL2.NotifyFinished();

			// create bundle, and move it
			/*var assetBundlePath = "Assets/BiomeDefense/Objects/CacheL2_AssetBundles/" + folder.Name; //+ ".assetbundle";
			BuildPipeline.BuildAssetBundles("Assets/BiomeDefense/Objects/CacheL2_AssetBundles", new[] {new AssetBundleBuild {assetBundleName = folder.Name, assetNames = new[] {mainPath}}}, BuildAssetBundleOptions.UncompressedAssetBundle, BuildTarget.StandaloneWindows);
			FileManager.root.Parent.GetFile(assetBundlePath).MoveTo(folder.GetFile("CacheL2/Model.assetbundle").CreateFolders().FullName);*/

			// delete asset
			//AssetDatabase.DeleteAsset(mainPath);
			
			timeL1.NotifyFinished();
		}
		if (!cacheL3Exists && Application.isEditor) // if CacheL3 doesn't exist, and we can create CacheL3, do so
		{
			timeL1 = timeInfo.AddChild("CacheL3 - create and save");

			if (cacheL2AndL3_asset == null)
			{
				timeL2 = timeL1.AddChild("Create asset");
				// old todo: fix that CacheL3 doesn't contain the materials or textures as subassets
				cacheL2AndL3_asset = CreateAssetForModel(model);
				//cacheL2AndL3_asset = CreateAssetForModel(V.Clone(model));
				timeL2.NotifyFinished();

				// maybe todo: add the asset to the "BiomeDefense/Objects/Models/Static_Generated" object automatically
			}
			var cacheL3Folder = folder.GetFolder("CacheL3").VCreate(); // create CacheL3 stub folder, that marks the asset above as active/to-be-used as CacheL3
			var writer = new StreamWriter(cacheL3Folder.GetFile("Main.vdf").Create());
			writer.Write("{}");
			writer.Close();

			timeL1.NotifyFinished();
		}
		#endif

		//VAssetProcessor_RuntimeData.makeTexturesReadable = false;

		return model;
	}
	public static GameObject LoadModel_FromCacheL1(DirectoryInfo folder, VDFNode rootNode, bool setModelPivotToTheModelCenter, TimeInfoNode timeInfo)
	{
		TimeInfoNode timeL1;

		// process data tree - wave 1
		// ==========

		timeL1 = timeInfo.AddChild("Process tree - wave 1");

		var result = new GameObject(folder.Name);
		//result.transform.SetParent(BD.main._gameObject.GetChild("#General/VModelImporter_TempHolder").transform, false);

		var modelInfo = new ModelInfo {folder = folder, rootNode = rootNode, objNodes = GetObjectNodes(rootNode), rootObj = result};
		foreach (string key in rootNode["objects"].mapChildren.Keys)
		{
			var childGameObject = LoadObject(rootNode["objects"][key], modelInfo, key, result);
			//childGameObject.transform.SetParent(result.transform, false);
			//childGameObject.name = key;

			//childGameObject.transform.localRotation = Quaternion.FromToRotation(Vector3.forward, Vector3.up) * childGameObject.transform.localRotation; // fix that model's "up" (Blender-z) shows in Unity as "forward" (Unity-y)
		}

		timeL1.NotifyFinished();

		// attach meshes, for mesh references
		// ==========

		timeL1 = timeInfo.AddChild("Process tree - wave 2");

		foreach (MeshFilter filter in result.GetComponentsInChildren<MeshFilter>(true))
			if (filter.sharedMesh == null)
			{
				var objWithMesh_name = modelInfo.objNodes[filter.name]["mesh"].primitiveValue.ToString();
				filter.sharedMesh = result.GetDescendent(objWithMesh_name).GetComponent<MeshFilter>().sharedMesh;
			}
		//foreach (SkinnedMeshRenderer renderer in result.GetComponentsInChildren<SkinnedMeshRenderer>(true))

		// attach bones to their meshes
		// ==========

		foreach (SkinnedMeshRenderer renderer in result.GetComponentsInChildren<SkinnedMeshRenderer>(true))
		{
			var armatureObj = result.GetDescendent(renderer.GetMeta<string>("armature name")); //renderer.GetMeta<GameObject>("armature");

			var mesh = renderer.sharedMesh;
			var bones = armatureObj.GetComponentsInChildren<Transform>(true).Except(new[] { armatureObj.transform }).OrderBy(a => a.name).ToArray();
			var boneBindPoses = new List<Matrix4x4>();
			foreach (Transform bone in bones)
			{
				boneBindPoses.Add(bone.worldToLocalMatrix * renderer.transform.localToWorldMatrix);
				//boneBindPoses.Add(bone.worldToLocalMatrix * armatureObj.transform.localToWorldMatrix);
				//boneBindPoses.Add(bone.worldToLocalMatrix * armatureObj.transform.GetChild(0).localToWorldMatrix);
				//boneBindPoses.Add(bone.worldToLocalMatrix * bone.parent.localToWorldMatrix);

				/*var extraRotation = bone.gameObject.GetMeta<Quaternion?>("ExtraRotation");
				if (extraRotation != null)
				{
					boneBindPoses[boneBindPoses.Count - 1] = Matrix4x4.TRS(Vector3.zero, Quaternion.Inverse(extraRotation.Value), Vector3.one) * boneBindPoses[boneBindPoses.Count - 1];
					//bone.parent.localRotation = extraRotation.Value * bone.parent.localRotation; // wait until after bind-poses are calculate, to apply this
				}*/
			}
			/*foreach (Transform bone in bones)
			{
				var extraRotation = bone.gameObject.GetMeta<Quaternion?>("ExtraRotation");
				if (extraRotation != null)
					bone.parent.localRotation = extraRotation.Value * bone.parent.localRotation; // wait until after bind-poses are calculate, to apply this
			}*/
			renderer.bones = bones.ToArray();
			//renderer.rootBone = result.GetComponentInChildren<Animation>().transform.GetChild(0); //result.transform.GetChild(0); // assumes there's only one animation-component/armature
			//renderer.rootBone = result.GetComponentInChildren<AnimationPlaceholder>().transform.GetChild(0);
			//renderer.rootBone = bones[0];
			renderer.rootBone = armatureObj.transform.GetChild(0);
			mesh.bindposes = boneBindPoses.ToArray();
		}

		timeL1.NotifyFinished();

		//result.SetLayer("Type", true);

		// post-processing
		// ==========

		timeL1 = timeInfo.AddChild("Process tree - wave 3");

		var submodel_main = result.GetChild("Root");
		var submodel_diagonal = result.GetChild("Root_Diagonal");
		var submodel_corner = result.GetChild("Root_Corner");

		if (setModelPivotToTheModelCenter) //centerSubmodelsAndTheirChildren)
			foreach (GameObject submodel in result.GetChildren())
			{
				submodel.transform.localPosition = Vector3.zero;
				submodel.SetPivotToLocalPoint(submodel.GetBounds(submodel.transform).center.NewZ(0), false); // make pivot-point of submodel equal its center

				/*submodel.transform.position -= submodel.GetBounds(result.transform).center.NewZ(0).ToVector3(); // make center of submodel equal the center of its parent (the model object)
				submodel.SetPivotToLocalPoint(submodel.GetBounds(submodel.transform).center.NewZ(0), true); // make pivot-point of submodel equal its center*/
			}

		if (submodel_diagonal)
		{
			submodel_diagonal.SetActive(false);
			// maybe temp; make diagonal subobjects line up from left-to-right, like the normal subobjects
			submodel_diagonal.transform.rotation = Quaternion.FromToRotation(new VVector3(1, 1, 0).ToVector3(), VVector3.right.ToVector3()) * result.GetChild("Root_Diagonal").transform.rotation;
		}
		if (submodel_corner)
		{
			submodel_main.SetActive(false);
			submodel_corner.SetActive(true); // use corner subobject for previews and such
		}

		timeL1.NotifyFinished();

		return result;
	}
	#if UNITY_EDITOR
	public static GameObject CreateAssetForModel(GameObject model)
	{
		var objectAssetPath = "Assets/BiomeDefense/Objects/Models/CacheL3/" + model.name + ".prefab";
		
		// create asset
		//AssetDatabase.DeleteAsset(mainPath);
		var result = PrefabUtility.CreatePrefab(objectAssetPath, model); //AssetDatabase.CreateAsset(model, assetPath);
		//PrefabUtility.CreatePrefab(mainPath, Object.Instantiate(model)); // create prefab based on clone, so that when prefab is destroyed, the model object is not affected
		//var result = AssetDatabase.LoadAssetAtPath<GameObject>(objectAssetPath);

		var newSubassetClones = new Dictionary<Object, Object>();
		//var newSubassetClones_materials = new Dictionary<string, Material>();

		foreach (Animation animation in model.GetComponentsInChildren<Animation>(true))
		{
			var states = animation.GetStates();

			var newAnimation = result.GetChild(animation.gameObject.GetPath(model)).GetComponent<Animation>();
			var newObj = newAnimation.gameObject;
			V.DestroyImmediate(newAnimation);
			newAnimation = newObj.AddComponent<Animation>();
			newAnimation.playAutomatically = false;

			foreach (AnimationState state in states)
			{
				if (!newSubassetClones.ContainsKey(state.clip))
				{
					newSubassetClones[state.clip] = V.Clone(state.clip);
					AssetDatabase.AddObjectToAsset(newSubassetClones[state.clip], result);
				}
				var clip = (AnimationClip)newSubassetClones[state.clip];
				newAnimation.AddClip(clip, clip.name);
			}
		}
		foreach (MeshFilter filter in model.GetComponentsInChildren<MeshFilter>(true))
		{
			var newFilter = result.GetChild(filter.gameObject.GetPath(model)).GetComponent<MeshFilter>();

			if (!newSubassetClones.ContainsKey(filter.sharedMesh))
			{
				newSubassetClones[filter.sharedMesh] = V.Clone(filter.sharedMesh);
				AssetDatabase.AddObjectToAsset(newSubassetClones[filter.sharedMesh], result);
			}
			var mesh = (Mesh)newSubassetClones[filter.sharedMesh];
			newFilter.sharedMesh = mesh;
		}
		foreach (MeshRenderer renderer in model.GetComponentsInChildren<MeshRenderer>(true))
		{
			var newRenderer = result.GetChild(renderer.gameObject.GetPath(model)).GetComponent<MeshRenderer>();
			var newMaterials = new Material[renderer.sharedMaterials.Length];
			for (var i = 0; i < renderer.sharedMaterials.Length; i++)
			{
				var material = renderer.sharedMaterials[i];

				// material
				/*var materialDataStr = material.GetDataStr();
				if (!newSubassetClones_materials.ContainsKey(material.GetDataStr()))
				{
					newSubassetClones_materials[material.GetDataStr()] = V.Clone(material);
					AssetDatabase.AddObjectToAsset(newSubassetClones_materials[material.GetDataStr()], mainAsset);
				}
				var newMaterial = newSubassetClones_materials[material.GetDataStr()];*/
				if (!newSubassetClones.ContainsKey(material))
				{
					newSubassetClones[material] = V.Clone(material);
					AssetDatabase.AddObjectToAsset(newSubassetClones[material], result);
				}
				var newMaterial = (Material)newSubassetClones[material];

				// texture
				if (material.mainTexture && !newSubassetClones.ContainsKey(material.mainTexture))
				{
					newSubassetClones[material.mainTexture] = V.Clone(material.mainTexture);
					//newSubassetClones[material.mainTexture] = V.CloneTexture((Texture2D)material.mainTexture);
					AssetDatabase.AddObjectToAsset(newSubassetClones[material.mainTexture], result);
				}
				newMaterial.mainTexture = material.mainTexture ? (Texture)newSubassetClones[material.mainTexture] : null;

				newMaterials[i] = newMaterial;
			}
			newRenderer.sharedMaterials = newMaterials;
		}
		foreach (SkinnedMeshRenderer renderer in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))
		{
			// mesh
			// ----------

			var newRenderer = result.GetChild(renderer.gameObject.GetPath(model)).GetComponent<SkinnedMeshRenderer>();

			if (!newSubassetClones.ContainsKey(renderer.sharedMesh))
			{
				newSubassetClones[renderer.sharedMesh] = V.Clone(renderer.sharedMesh);
				AssetDatabase.AddObjectToAsset(newSubassetClones[renderer.sharedMesh], result);
			}
			var mesh = (Mesh)newSubassetClones[renderer.sharedMesh];
			newRenderer.sharedMesh = mesh;

			// materials
			// ----------

			var newMaterials = new Material[renderer.sharedMaterials.Length];
			for (var i = 0; i < renderer.sharedMaterials.Length; i++)
			{
				var material = renderer.sharedMaterials[i];

				// material
				if (!newSubassetClones.ContainsKey(material))
				{
					newSubassetClones[material] = V.Clone(material);
					AssetDatabase.AddObjectToAsset(newSubassetClones[material], result);
				}
				var newMaterial = (Material)newSubassetClones[material];

				// texture
				if (material.mainTexture && !newSubassetClones.ContainsKey(material.mainTexture))
				{
					newSubassetClones[material.mainTexture] = V.Clone(material.mainTexture);
					//newSubassetClones[material.mainTexture] = V.CloneTexture((Texture2D)material.mainTexture);
					AssetDatabase.AddObjectToAsset(newSubassetClones[material.mainTexture], result);
				}
				newMaterial.mainTexture = material.mainTexture ? (Texture)newSubassetClones[material.mainTexture] : null;

				newMaterials[i] = newMaterial;
			}
			newRenderer.sharedMaterials = newMaterials;
		}
		
		return result;
	}
	#endif

	public static GameObject LoadObject(VDFNode objNode, ModelInfo modelInfo, string objName = null, GameObject parentObj = null, bool isRootBone = false)
	{
		var result = new GameObject("Model");
		//result.SetLayer("Type", true);

		// maybe temp; fix for in-animation bones not being able to figure out their ancestor-line
		result.name = objName;
		result.transform.SetParent(parentObj.transform, false);

		//ConvertObjectNodeFromZUpToYUp(objNode, isRootBone);

		// transform
		// ==========

		result.transform.localPosition = new VVector3(objNode["p"][0], objNode["p"][1], objNode["p"][2]).ToVector3(); //objNode["p"].ToObject<Vector3>();
		//result.transform.localEulerAngles = new Vector3(objNode["r"][0], objNode["r"][1], objNode["r"][2]); //objNode["r"].ToObject<Vector3>();
		result.transform.localRotation = new VVector4(objNode["r"][0], objNode["r"][1], objNode["r"][2], objNode["r"][3]).ToQuaternion();
		if (objNode["s"] != null)
			result.transform.localScale = new VVector3(objNode["s"][0], objNode["s"][1], objNode["s"][2]).ToVector3(); //objNode["s"].ToObject<Vector3>();

		// mesh (and materials)
		// ==========

		if (objNode["mesh"] != null) //|| folder.GetFile("CacheL1/" + objName + ".mesh").Exists)
		{
			var meshNode = objNode["mesh"];

			Mesh mesh;
			List<Material> materials;
			if (meshNode.primitiveValue != null) // if reference
			{
				//if (meshNode.primitiveValue != null) // if the "mesh" is really a mesh-reference, only start using the referenced mesh-data here (for the materials data) (the referenced mesh itself will be attached later)
				//	meshNode = modelInfo.objNodes[meshNode.primitiveValue.ToString()]["mesh"];

				var sourceObject = modelInfo.rootObj.GetDescendent(meshNode.As<string>()); // this relies on source-object always coming earlier in VDF than ones referencing it
				mesh = sourceObject.GetComponent<MeshFilter>().sharedMesh;
				materials = sourceObject.GetComponent<MeshRenderer>().sharedMaterials.ToList();
			}
			else
			{
				if (modelInfo.folder.GetFile("CacheL1/" + objName + ".mesh").Exists)
					mesh = MeshSerializer.ReadMesh(File.ReadAllBytes(modelInfo.folder.GetFile("CacheL1/" + objName + ".mesh").FullName));
				else
				{
					var unityVertexes = new List<VVector3>();
					var unityNormals = new List<VVector3>();
					var unityUVs = new List<VVector2>();
					var unitySubmeshTriangles = new List<List<int>>();
					var unityBoneWeights = new List<BoneWeight>();

					var vertexNodes = meshNode["vertices"].listChildren;
					var faceNodes = meshNode["faces"].listChildren;

					var armatureName = meshNode["armature"].As<string>(); //meshNode["armature"] != null ? (string)meshNode["armature"] : null;
					List<string> boneNames = null;
					if (armatureName != null)
					{
						VDFNode armatureObjNode = modelInfo.objNodes[armatureName]; //FindObjectNode(modelInfo.rootNode, armatureName);
						boneNames = GetBoneNames(armatureObjNode["armature"]["bones"], true).OrderBy(a=>a).ToList();
					}

					for (var i = 0; i < (meshNode["materials"] != null ? meshNode["materials"].listChildren.Count : 1); i++) // for each material, load its faces (for now at least, every face must have an associated material)
					{
						var unityCurrentSubmeshTriangles = new List<int>();

						var faceNodeIndex = 0;
						foreach (VDFNode faceNode in faceNodes)
						{
							if ((i == 0 && !faceNode.listChildren.Any(a=>a.isMap)) || (faceNode.listChildren.Last()["material"] != null && faceNode.listChildren.Last()["material"] == i))
							{
								var faceVertexNodes = faceNode.listChildren.Where(a=>!a.isMap).ToList();
								foreach (VDFNode faceVertexNode in faceVertexNodes)
								{
									var vertexNode = vertexNodes[faceVertexNode];
									unityVertexes.Add(new VVector3(vertexNode["p"][0], vertexNode["p"][1], vertexNode["p"][2]));
									unityNormals.Add(new VVector3(vertexNode["n"][0], vertexNode["n"][1], vertexNode["n"][2]));

									var uvNode = vertexNode.mapChildren.ContainsKey("uv") ? vertexNode["uv"] : vertexNode["uv_face" + faceNodeIndex]; // we currently only use the first uv-layer's uvs
									//var uvNode = vertexNode.mapChildren[vertexNode.mapChildren.Keys.First(a=>a.StartsWith("uv"))]; // maybe temp; for uvs, only ever use the first uv of the first uv-layer
									unityUVs.Add(uvNode != null ? new VVector2(uvNode[0], uvNode[1]) : VVector2.zero);

									/*var boneWeightData = new Dictionary<string, float>();
									if (vertexNode.mapChildren.ContainsKey("boneWeights"))
										foreach (var boneName in vertexNode["boneWeights"].mapChildren.Keys)
											boneWeightData.Add(boneName, vertexNode["boneWeights"][boneName]);
									boneWeightDatas.Add(boneWeightData);*/

									var boneWeight = new BoneWeight();
									if (vertexNode["bW"] != null)
									{
										var boneWeightBoneIndex = 0;

										var weightScaleValue = 1 / vertexNode["bW"].mapChildren.OrderByDescending(a=>(float)a.Value).Take(4).Sum(a=>(float)a.Value);
										foreach (KeyValuePair<string, VDFNode> pair in vertexNode["bW"].mapChildren.OrderByDescending(a=>(float)a.Value)) // sort bone-weights by weight, to ensure the four most important are added
										{
											var boneIndex = boneNames.IndexOf(pair.Key);
											if (boneWeightBoneIndex == 0)
											{
												boneWeight.boneIndex0 = boneIndex;
												boneWeight.weight0 = pair.Value * weightScaleValue;
											}
											else if (boneWeightBoneIndex == 1)
											{
												boneWeight.boneIndex1 = boneIndex;
												boneWeight.weight1 = pair.Value * weightScaleValue;
											}
											else if (boneWeightBoneIndex == 2)
											{
												boneWeight.boneIndex2 = boneIndex;
												boneWeight.weight2 = pair.Value * weightScaleValue;
											}
											else if (boneWeightBoneIndex == 3)
											{
												boneWeight.boneIndex3 = boneIndex;
												boneWeight.weight3 = pair.Value * weightScaleValue;
											}
											//else
											//	Debug.Log("More than 4 bone-weights found for vertex: " + faceVertexNode);
											boneWeightBoneIndex++;
										}
									}
									unityBoneWeights.Add(boneWeight);
								}

								var firstUnityVertexForFaceIndex = unityVertexes.Count - faceVertexNodes.Count;
								if (faceVertexNodes.Count == 4)
								{
									/*unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 1);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 2);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 2);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 3);*/
									// since we're changing from right-handed to left-handed, reverse all triangle vertex-lists (so the winding is correct)
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 2);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 1);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 3);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 2);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex);
								}
								else
								{
									/*unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 1);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 2);*/
									// since we're changing from right-handed to left-handed, reverse all triangle vertex-lists (so the winding is correct)
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 2);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex + 1);
									unityCurrentSubmeshTriangles.Add(firstUnityVertexForFaceIndex);
								}
							}

							faceNodeIndex++;
						}

						unitySubmeshTriangles.Add(unityCurrentSubmeshTriangles);
					}

					mesh = new Mesh();
					mesh.vertices = unityVertexes.Select(a=>a.ToVector3()).ToArray();
					mesh.normals = unityNormals.Select(a=>a.ToVector3()).ToArray();
					mesh.uv = unityUVs.Select(a=>a.ToVector2(false)).ToArray(); //mesh.uv = unityUVs.Select(a=>new Vector2(0, 0)).ToArray();
					mesh.boneWeights = unityBoneWeights.ToArray();
					//mesh.triangles = unityTriangles.ToArray();
					mesh.subMeshCount = unitySubmeshTriangles.Count;
					for (var i = 0; i < unitySubmeshTriangles.Count; i++)
						mesh.SetTriangles(unitySubmeshTriangles[i].ToArray(), i);

					// I think this removes duplicate vertexes; helpful, as it means I can just add each face-vertex in anew, without checking if one's already added with same pos, normal, and uv
					//mesh.Optimize();
					//VMeshTools.OptimizeMesh(mesh);
					var meshData = MeshData.FromMesh(mesh);
					meshData.Optimize();
					meshData.PrepareArrays();
					meshData.ToMesh(mesh);

					mesh.RecalculateNormals(); // maybe temp; exporter currently doesn't export vertex normals specific to faces ([edge/corner]-vertex normals are averages of neighbor-faces' normals), and we're too lazy to calculate (and use for [edge/corner]-vertexes) the face normal

					File.WriteAllBytes(modelInfo.folder.GetFile("CacheL1/" + objName + ".mesh").CreateFolders().FullName, MeshSerializer.WriteMesh(mesh, false)); //true));
				}
				//CalculateTangents(mesh);

				// renderer
				// ----------
				
				materials = new List<Material>();
				if (meshNode["materials"] != null)
					foreach (VDFNode materialNode in meshNode["materials"].listChildren)
					{
						/*var shaderName = "Diffuse"; //Legacy Shaders/Diffuse";
						if (materialNode.mapChildren.ContainsKey("transparency") && materialNode["transparency"] == true)
							shaderName = "Legacy Shaders/Transparent/Diffuse";
						var material = new Material(Shader.Find(shaderName));*/
						Material material;
						if (materialNode["unlitShader"].As<bool>())
							material = new Material(Shader.Find("Unlit/Texture"));
						else if (materialNode["leafShader"].As<bool>())
						{
							material = new Material(Shader.Find("Nature/Tree Soft Occlusion Leaves"));
							material.color = materialNode["diffuseColor"] != null ? V.HexStringToColor(materialNode["diffuseColor"]) : Color.white;
						}
						else
							if (!materialNode["transparency"].As<bool>())
							{
								material = new Material(materialNode["doubleSided"].As<bool>() ? Shader.Find("Standard_DoubleSided") : Shader.Find("Standard"));
								material.color = materialNode["diffuseColor"] != null ? V.HexStringToColor(materialNode["diffuseColor"]) : Color.white;
							}
							else
								if (materialNode["alphaMin"] != null)
								{
									material = new Material(materialNode["doubleSided"].As<bool>() ? Shader.Find("Standard_DoubleSided") : Shader.Find("Standard"));
									material.color = materialNode["diffuseColor"] != null ? V.HexStringToColor(materialNode["diffuseColor"]) : Color.white;

									material.SetBlendMode(ClassExtensions.BlendMode.Cutout);
									material.SetFloat("_Cutoff", materialNode["alphaMin"]);
									material.SetFloat("_Glossiness", 1);
								}
								else
								{
									material = new Material(materialNode["doubleSided"].As<bool>() ? Shader.Find("Standard_DoubleSided") : Shader.Find("Standard"));
									material.color = materialNode["diffuseColor"] != null ? V.HexStringToColor(materialNode["diffuseColor"]) : Color.white;

									material.SetBlendMode(ClassExtensions.BlendMode.Fade);
									if (materialNode["alpha"] != null)
										material.color = material.color.NewA(materialNode["alpha"]);
								}

						if (materialNode["texture"] != null)
						{
							material.color = new Color(1, 1, 1, 1); // diffuse-color is usually not used for materials with textures
							var texturePath = modelInfo.folder.GetFile("Textures/" + materialNode["texture"]).FullName;
							if (!modelInfo.textureCache.ContainsKey(texturePath))
							{
								var texture = new Texture2D(0, 0);
								texture.LoadImage(File.ReadAllBytes(modelInfo.folder.GetFile("Textures/" + materialNode["texture"]).FullName));
								//texture.wrapMode = TextureWrapMode.Repeat;

								// copy pixels into new texture, so mip-maps gets created
								var texture_final = new Texture2D(texture.width, texture.height);
								texture_final.SetPixels32(texture.GetPixels32());
								texture_final.Apply();

								modelInfo.textureCache.Add(texturePath, texture_final);
							}
							material.mainTexture = modelInfo.textureCache[texturePath];
						}

						materials.Add(material);
					}
			}

			if (meshNode["armature"] != null)
			{
				var renderer = result.AddComponent<SkinnedMeshRenderer>();
				renderer.sharedMesh = mesh;
				//renderer.materials = materials.ToArray();
				renderer.sharedMaterials = materials.ToArray();
				//renderer.bones = null;
				//renderer.rootBone = null;
				renderer.SetMeta("armature name", meshNode["armature"].primitiveValue);
			}
			else
			{
				var filter = result.AddComponent<MeshFilter>();
				filter.sharedMesh = mesh;
				var renderer = result.AddComponent<MeshRenderer>();
				//renderer.materials = materials.ToArray();
				renderer.sharedMaterials = materials.ToArray();
			}
		}

		// armature
		// ==========

		if (objNode["armature"] != null)
		{
			result.SetMeta("is armature", true); // maybe temp

			var boneNodes = objNode["armature"]["bones"];
			foreach (string boneName in boneNodes.mapChildren.Keys)
			{
				var childGameObject = LoadObject(boneNodes[boneName], modelInfo, boneName, result, true); // bones are just game-objects in Unity
				//childGameObject.transform.SetParent(result.transform, false);
				//childGameObject.name = boneName;

				// maybe temp; fix for that Blender's bones have a 'rest' rotation of pointing toward y+, rather than z+
				//childGameObject.transform.localRotation = Quaternion.FromToRotation(Vector3.up, Vector3.forward) * childGameObject.transform.localRotation;
				//childGameObject.transform.localRotation = Quaternion.FromToRotation(Vector3.forward, Vector3.up) * childGameObject.transform.localRotation;
				/*var rotation = childGameObject.transform.localRotation;
				var yOld = rotation.y;
				rotation.y = -rotation.z;
				rotation.z = yOld;
				childGameObject.transform.localRotation = rotation;*/
				//childGameObject.SetMeta("ExtraRotation", Quaternion.FromToRotation(Vector3.forward, Vector3.up)); // maybe todo: add this back
				//result.transform.localRotation = Quaternion.FromToRotation(Vector3.forward, Vector3.up) * result.transform.localRotation;
			}
		}

		// animation
		// ==========

		if (objNode["animations"] != null)
		{
			//var anim = result.AddComponent<Animation>();
			var anim = modelInfo.rootObj.AddComponent<Animation>();
			anim.playAutomatically = false;
			foreach (string animationName in objNode["animations"].mapChildren.Keys)
			{
				var animationNode = objNode["animations"][animationName];
				var animationClip = new AnimationClip();
				//animationClip.name = animationName;
				animationClip.legacy = true;
				animationClip.frameRate = animationNode["fps"];

				foreach (string boneName in animationNode["boneKeyframes"].mapChildren.Keys)
				{
					var positionCurve_x = new AnimationCurve();
					var positionCurve_y = new AnimationCurve();
					var positionCurve_z = new AnimationCurve();
					var rotationCurve_x = new AnimationCurve();
					var rotationCurve_y = new AnimationCurve();
					var rotationCurve_z = new AnimationCurve();
					var rotationCurve_w = new AnimationCurve();
					var scaleCurve_x = new AnimationCurve();
					var scaleCurve_y = new AnimationCurve();
					var scaleCurve_z = new AnimationCurve();
					
					var keyframesNode = animationNode["boneKeyframes"][boneName];
					VVector4? lastFrameRotation = null;
					foreach (string frame in keyframesNode.mapChildren.Keys)
					{
						var keyframeNode = keyframesNode[frame];
						//ConvertKeyframeNodeFromZUpToYUp(keyframeNode);
						var time = int.Parse(frame) / animationClip.frameRate; //int.Parse(frame)
						/*positionCurve_x.AddKey(time, keyframeNode["position"][0]);
						positionCurve_y.AddKey(time, keyframeNode["position"][1]);
						positionCurve_z.AddKey(time, keyframeNode["position"][2]);
						rotationCurve_x.AddKey(time, keyframeNode["rotation"][0]);
						rotationCurve_y.AddKey(time, keyframeNode["rotation"][1]);
						rotationCurve_z.AddKey(time, keyframeNode["rotation"][2]);
						rotationCurve_w.AddKey(time, keyframeNode["rotation"][3]);
						scaleCurve_x.AddKey(time, keyframeNode["scale"][0]);
						scaleCurve_y.AddKey(time, keyframeNode["scale"][1]);
						scaleCurve_z.AddKey(time, keyframeNode["scale"][2]);*/

						var position = new VVector3(keyframeNode["p"][0], keyframeNode["p"][1], keyframeNode["p"][2]);
						var rotation = new VVector4(keyframeNode["r"][0], keyframeNode["r"][1], keyframeNode["r"][2], keyframeNode["r"][3]);
						var scale = keyframeNode["s"] != null ? new VVector3(keyframeNode["s"][0], keyframeNode["s"][1], keyframeNode["s"][2]) : VVector3.one;

						// for fixing flipping/flickering/discontinuity (where the rotation slerp "takes the long way around"):
						// "try taking the dot product of your two quaternions (i.e., the 4-D dot product), and if the dot product is negative, replace your quaterions q1 and q2 with -q1 and q2 before performing Slerp"
						if (lastFrameRotation != null && VVector4.Quaternion_Dot(lastFrameRotation.Value, rotation) < 0)
							//rotation = VVector4.Quaternion_Inverse(rotation);
							rotation = -rotation;
						lastFrameRotation = rotation;

						// apparently the "local position" in Unity animation clips, is actually the position-relative-to-armature; 
						/*var boneObj = modelInfo.rootObj.GetDescendent(boneName).gameObject;
						var armatureObj = boneObj.GetParents().First(a=>a.GetMeta<bool?>("is armature") == true);
						var boneBaseMatrix_relativeToArmature = armatureObj.transform.localToWorldMatrix.inverse * boneObj.transform.localToWorldMatrix;*/
						/*position = boneBaseMatrix_relativeToArmature * position;
						//rotation = boneBaseMatrix_relativeToArmature * rotation;
						rotation = (boneBaseMatrix_relativeToArmature * Matrix4x4.TRS(Vector3.zero, rotation, Vector3.one)).GetRotation();
						scale = boneBaseMatrix_relativeToArmature * scale;*/
						// old: todo: make sure this is correct
						/*position = boneBaseMatrix_relativeToArmature.GetPosition() + position;
						rotation = boneBaseMatrix_relativeToArmature.GetRotation() * rotation;
						//var rot1 = boneBaseMatrix_relativeToArmature.GetRotation();
						//rotation = new Quaternion(rot1.x + rotation.x, rot1.x + rotation.x, rot1.x + rotation.x, rot1.x + rotation.x);
						//scale = boneBaseMatrix_relativeToArmature.GetScale() + scale;*/

						var position_final = position.ToVector3();
						var rotation_final = rotation.ToQuaternion();
						var scale_final = scale.ToVector3();

						positionCurve_x.AddKey(time, position_final.x);
						positionCurve_y.AddKey(time, position_final.y);
						positionCurve_z.AddKey(time, position_final.z);
						rotationCurve_x.AddKey(time, rotation_final.x);
						rotationCurve_y.AddKey(time, rotation_final.y);
						rotationCurve_z.AddKey(time, rotation_final.z);
						rotationCurve_w.AddKey(time, rotation_final.w);
						scaleCurve_x.AddKey(time, scale_final.x);
						scaleCurve_y.AddKey(time, scale_final.y);
						scaleCurve_z.AddKey(time, scale_final.z);
					}

					var bonePath_transforms = new List<Transform>();
					var bone = result.GetDescendent(boneName).gameObject;
					var currentTransform = bone.transform;
					//while (currentTransform != result.transform)
					while (currentTransform != modelInfo.rootObj.transform)
					{
						bonePath_transforms.Insert(0, currentTransform);
						currentTransform = currentTransform.parent;
					}
					string bonePath = String.Join("/", bonePath_transforms.Select(a=>a.name).ToArray());

					animationClip.SetCurve(bonePath, typeof(Transform), "localPosition.x", positionCurve_x);
					animationClip.SetCurve(bonePath, typeof(Transform), "localPosition.y", positionCurve_y);
					animationClip.SetCurve(bonePath, typeof(Transform), "localPosition.z", positionCurve_z);
					/*animationClip.SetCurve(bonePath, typeof(Transform), "localEulerAngles.x", rotationCurve_x);
					animationClip.SetCurve(bonePath, typeof(Transform), "localEulerAngles.y", rotationCurve_y);
					animationClip.SetCurve(bonePath, typeof(Transform), "localEulerAngles.z", rotationCurve_z);*/
					animationClip.SetCurve(bonePath, typeof(Transform), "localRotation.x", rotationCurve_x);
					animationClip.SetCurve(bonePath, typeof(Transform), "localRotation.y", rotationCurve_y);
					animationClip.SetCurve(bonePath, typeof(Transform), "localRotation.z", rotationCurve_z);
					animationClip.SetCurve(bonePath, typeof(Transform), "localRotation.w", rotationCurve_w);
					animationClip.SetCurve(bonePath, typeof(Transform), "localScale.x", scaleCurve_x);
					animationClip.SetCurve(bonePath, typeof(Transform), "localScale.y", scaleCurve_y);
					animationClip.SetCurve(bonePath, typeof(Transform), "localScale.z", scaleCurve_z);
				}

				anim.AddClip(animationClip, animationName);
			}
		}

		// extra
		// ==========

		//if (objNode.mapChildren.ContainsKey("anchorToTerrain"))
		//	result.SetMeta("anchor to terrain", true);
		var info = result.AddComponent<VObject_GameObjectInfo>();
		info.anchorToTerrain = objNode["anchorToTerrain"] != null; //.As<bool?>() == true;
		info.anchorVertexesToTerrain = objNode["anchorVertexesToTerrain"] != null; //.As<bool?>() == true;
		if (objNode["gateGrate_openPosition"] != null)
			//info.gateGrate_openPosition = objNode["gateGrate_openPosition"].ToObject<VVector3>();
			info.gateGrate_openPosition = new VVector3(objNode["gateGrate_openPosition"][0], objNode["gateGrate_openPosition"][1], objNode["gateGrate_openPosition"][2]);

		// children
		// ==========

		if (objNode["children"] != null)
			foreach (string key in objNode["children"].mapChildren.Keys)
				try
				{
					var childGameObject = LoadObject(objNode["children"][key], modelInfo, key, result);
					//childGameObject.transform.SetParent(result.transform, false);
					//childGameObject.name = key;
				}
				catch (Exception ex)
				{
					ex.AddToMessage("\nSub-object name:" + key);
					throw;
				}

		return result;
	}

	/*static void ConvertObjectNodeFromZUpToYUp(VDFNode objNode, bool isRootBone = false) // change from VModel's z-up to Unity's y-up, by swapping y and z
	{
		SwapItems(objNode["p"].listChildren, 1, 2);
		SwapItems(objNode["r"].listChildren, 1, 2);
		//objNode["r"][2].primitiveValue = -(double)objNode["r"][2];
		ReverseValues(objNode["r"].listChildren, 0, 3); // since we're changing from right-handed to left-handed, reverse all around-axis rotation angles
		/*if (isRootBone)
		{
			var rotation = new Quaternion(objNode["r"][0], objNode["r"][1], objNode["r"][2], objNode["r"][3]);
			rotation = Quaternion.FromToRotation(Vector3.forward, Vector3.up) * rotation;
			objNode["r"][0].primitiveValue = rotation.x;
			objNode["r"][1].primitiveValue = rotation.y;
			objNode["r"][2].primitiveValue = rotation.z;
			objNode["r"][3].primitiveValue = rotation.w;
		}*#/
		if (objNode.mapChildren.ContainsKey("s"))
			SwapItems(objNode["s"].listChildren, 1, 2);

		if (objNode.mapChildren.ContainsKey("mesh"))
		{
			var meshNode = objNode["mesh"];
			if (meshNode.mapChildren.ContainsKey("vertices"))
				foreach (VDFNode vertexNode in meshNode["vertices"].listChildren)
				{
					SwapItems(vertexNode["p"].listChildren, 1, 2);
					SwapItems(vertexNode["n"].listChildren, 1, 2);
				}
			// since we're changing from right-handed to left-handed, reverse all triangle vertex-lists (so the winding is correct)
			if (meshNode.mapChildren.ContainsKey("faces"))
				foreach (VDFNode faceNode in meshNode["faces"].listChildren)
					if (faceNode.listChildren.Last().isMap)
						ReverseRange(faceNode.listChildren, 0, faceNode.listChildren.Count - 1);
					else
						faceNode.listChildren.Reverse();
		}
	}
	static void ConvertKeyframeNodeFromZUpToYUp(VDFNode keyframeNode) { ConvertObjectNodeFromZUpToYUp(keyframeNode); }*/

	/*static void ConvertObjectNodeFromZUpToYUp(VDFNode objNode, bool isRootBone = false) // change from VModel's z-up to Unity's y-up, by inverting Blender-y/Unity-z
	{
		objNode["position"][1].primitiveValue = -(double)objNode["position"][1];
		objNode["rotation"][1].primitiveValue = -(double)objNode["rotation"][1];
		ReverseValues(objNode["rotation"].listChildren, 0, 3); // since we're changing from right-handed to left-handed, reverse all around-axis rotation angles
		//objNode["scale"][1].primitiveValue = -(double)objNode["scale"][1];

		if (objNode.mapChildren.ContainsKey("mesh"))
		{
			var meshNode = objNode["mesh"];
			if (meshNode.mapChildren.ContainsKey("vertices"))
				foreach (VDFNode vertexNode in meshNode["vertices"].listChildren)
				{
					vertexNode["position"][1].primitiveValue = -(double)vertexNode["position"][1];
					vertexNode["normal"][1].primitiveValue = -(double)vertexNode["normal"][1];
				}
			if (meshNode.mapChildren.ContainsKey("faces"))
				foreach (VDFNode faceNode in meshNode["faces"].listChildren)
					if (faceNode.listChildren.Last().isMap)
						ReverseRange(faceNode.listChildren, 0, faceNode.listChildren.Count - 1);
					else
						faceNode.listChildren.Reverse();
		}
	}
	static void ConvertKeyframeNodeFromZUpToYUp(VDFNode keyframeNode) { ConvertObjectNodeFromZUpToYUp(keyframeNode); }*/

	/*static void SwapItems(List<VDFNode> list, int index1, int index2, bool reverseNewA = false, bool reverseNewB = false)
	{
		var temp = list[index1];
		list[index1] = list[index2];
		list[index2] = temp;
		if (reverseNewA)
			list[index1].primitiveValue = -(double)list[index1];
		if (reverseNewB)
			list[index2].primitiveValue = -(double)list[index2];
	}
	static void ReverseRange(List<VDFNode> list, int startIndex, int enderIndex)
	{
		var sublist = list.GetRange(startIndex, enderIndex - startIndex);
		sublist.Reverse();
		for (var i = 0; i < sublist.Count; i++)
			list[startIndex + i] = sublist[i];
	}
	static void ReverseValues(List<VDFNode> list, int startIndex = -1, int enderIndex = -1)
	{
		var sublist = startIndex != -1 ? list.GetRange(startIndex, enderIndex - startIndex) : list;
		for (var i = 0; i < sublist.Count; i++)
			sublist[i].primitiveValue = -(double)sublist[i];
	}*/

	/*static VDFNode FindObjectNode(VDFNode obj, string objectName)
	{
		foreach (string key in obj.mapChildren.Keys)
		{
			if (key == objectName)
				return obj[key];
			var childResult = FindObjectNode(obj[key], objectName);
			if (childResult != null)
				return childResult;
		}
		return null;
	}*/
	static Dictionary<string, VDFNode> GetObjectNodes(VDFNode node, string key = null)
	{
		var result = new Dictionary<string, VDFNode>();
		foreach (string childKey in node.mapChildren.Keys)
		{
			if (key == "objects" || key == "children")
				result.Add(childKey, node[childKey]);

			/*var childObjectNodes = GetObjectNodes(node[childKey], childKey);
			foreach (var childChildKey in childObjectNodes.Keys)
			{
				if (result.ContainsKey(childChildKey))
					V.Nothing();
				result.Add(childChildKey, childObjectNodes[childChildKey]);
			}*/
			result.AddDictionary(GetObjectNodes(node[childKey], childKey));
		}
		return result;
	}
	static List<string> GetBoneNames(VDFNode obj, bool objIsChildrenMap)
	{
		var result = new List<string>();
		foreach (string key in obj.mapChildren.Keys)
		{
			if (objIsChildrenMap)
				result.Add(key);
			result.AddRange(GetBoneNames(obj[key], key == "children"));
		}
		return result;
	}

	/*static void CalculateTangents(Mesh mesh)
	{
		var tan1 = new Vector3[mesh.vertexCount];
		var tan2 = new Vector3[mesh.vertexCount];

		var vertexes = mesh.vertices;
		var triangles = mesh.triangles;
		for (int a = 0; a < triangles.Length; a += 3)
		{
			int i1 = triangles[a + 0];
			int i2 = triangles[a + 1];
			int i3 = triangles[a + 2];

			Vector3 v1 = vertexes[i1];
			Vector3 v2 = vertexes[i2];
			Vector3 v3 = vertexes[i3];

			Vector2 w1 = mesh.uv[i1];
			Vector2 w2 = mesh.uv[i2];
			Vector2 w3 = mesh.uv[i3];

			float x1 = v2.x - v1.x;
			float x2 = v3.x - v1.x;
			float y1 = v2.y - v1.y;
			float y2 = v3.y - v1.y;
			float z1 = v2.z - v1.z;
			float z2 = v3.z - v1.z;

			float s1 = w2.x - w1.x;
			float s2 = w3.x - w1.x;
			float t1 = w2.y - w1.y;
			float t2 = w3.y - w1.y;

			float div = s1 * t2 - s2 * t1;
			float r = Mathf.Approximately(div, 0f) ? 0f : 1f / div;

			var sdir = new Vector3((t2 * x1 - t1 * x2) * r, (t2 * y1 - t1 * y2) * r, (t2 * z1 - t1 * z2) * r);
			var tdir = new Vector3((s1 * x2 - s2 * x1) * r, (s1 * y2 - s2 * y1) * r, (s1 * z2 - s2 * z1) * r);

			tan1[i1] += sdir;
			tan1[i2] += sdir;
			tan1[i3] += sdir;

			tan2[i1] += tdir;
			tan2[i2] += tdir;
			tan2[i3] += tdir;
		}

		var tangents = new Vector4[mesh.vertexCount];
		for (var i = 0; i < mesh.vertexCount; ++i)
		{
			Vector3 n = mesh.normals[i];
			Vector3 t = tan1[i];

			Vector3 tmp = (t - n * Vector3.Dot(n, t)).normalized;
			float w = (Vector3.Dot(Vector3.Cross(n, t), tan2[i]) < 0.0f) ? -1.0f : 1.0f;
			tangents[i] = new Vector4(tmp.x, tmp.y, tmp.z, w);
		}
		mesh.tangents = tangents;
	}*/
}